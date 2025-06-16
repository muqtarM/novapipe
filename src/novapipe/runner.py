import asyncio
import os
from asyncio import Semaphore
import logging
import jinja2
import time
from collections import defaultdict, deque
from typing import Dict, Set, List, Any, Optional, Union
from prometheus_client import Counter, Histogram, Gauge

from .tasks import task_registry, load_plugins
from .models import Pipeline, TaskModel

logger = logging.getLogger("novapipe")

# ---- Prometheus metrics ----
TASK_STATUS = Counter(
    "novapipe_task_status_total",
    "Count of task executions by status",
    ["pipeline", "task", "status"],
)

TASK_DURATION = Histogram(
    "novapipe_task_duration_seconds",
    "Task execution duration",
    ["pipeline", "task", "status"],
)

PIPELINE_STATUS = Counter(
    "novapipe_pipeline_status_total",
    "Count of pipeline runs by status",
    ["pipeline", "status"],
)

PIPELINE_DURATION = Histogram(
    "novapipe_pipeline_duration_seconds",
    "Pipeline run duration in seconds",
    ["pipeline"],
)


class TaskMetrics:
    """
    Stores summary info for one task:
      - attempts: total attempts made (1 + retries)
      - status: "success", "failed_ignored", or "failed_abort"
      - duration_secs: wall‐clock time from first attempt start to final outcome
      - error: error message (if any; null on success)
    """
    def __init__(self, name: str):
        self.name: str = name
        self.attempts: int = 0
        self.status: Optional[str] = None
        self.start_time: Optional[float] = None
        self.duration_secs: Optional[float] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "attempts": self.attempts,
            "status": self.status,
            "duration_secs": self.duration_secs,
            "error": self.error,
        }


class PipelineRunSummary:
    """
    Collects a dict of TaskSummary, keyed by task name.
    """
    def __init__(self):
        self.tasks: Dict[str, TaskMetrics] = {}

    def record_start(self, name: str):
        ts = TaskMetrics(name)
        self.tasks[name] = ts
        ts.start_time = time.time()  # for intermediate tracking

    def record_success(self, name: str, attempts: int):
        ts = self.tasks[name]
        ts.attempts = attempts
        ts.status = "success"
        ts.duration_secs = time.time() - ts.start_time
        ts.error = None

    def record_failed_ignored(self, name: str, attempts: int, error: Exception):
        ts = self.tasks[name]
        ts.attempts = attempts
        ts.status = "failed_ignored"
        ts.duration_secs = time.time() - ts.start_time
        ts.error = repr(error)

    def record_failed_abort(self, name: str, attempts: int, error: Exception):
        ts = self.tasks[name]
        ts.attempts = attempts
        ts.status = "failed_abort"
        ts.duration_secs = time.time() - ts.start_time
        ts.error = repr(error)

    def record_skipped(self, name: str):
        ts = TaskMetrics(name)
        ts.attempts = 0
        ts.status = "skipped"
        ts.duration_secs = 0.0
        ts.error = None
        ts.start_time = time.time()
        self.tasks[name] = ts

    def to_list(self) -> List[Dict[str, Any]]:
        return [ts.to_dict() for ts in self.tasks.values()]


class PipelineRunner:
    """
    Executes a validated Pipeline of Steps, supporting async tasks.
    """
    def __init__(self, raw_data: dict, pipeline_name: str) -> None:
        # 1. Parse & validate YAML into Pydantic models
        self.pipeline = Pipeline.model_validate(raw_data)
        # 2. Build in-memory DAG structures
        self._build_graph()
        self.pipeline_name = pipeline_name

        # Prepare summary
        self._summary = PipelineRunSummary()

        # Shared context: task_name → return_value
        self.context: Dict[str, Any] = {}

        # Jinja2 environment for templating
        self._jinja_env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            autoescape=False
        )
        # make python build-ins available in templates
        self._jinja_env.globals.update({
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'len': len,
        })

        # Build semaphore for any tasks that declared max_concurrency
        self._resource_semaphores: Dict[Optional[str], Semaphore] = {}
        for t in self.tasks_by_name.values():
            tag = t.resource_tag
            if tag and t.max_concurrency:
                # only one semaphore per tag
                if tag in self._resource_semaphores:
                    # pick the smallest limit if multiple tasks share the tag
                    existing = self._resource_semaphores[tag]._value
                    limit = min(existing, t.max_concurrency)
                    self._resource_semaphores[tag] = Semaphore(limit)
                else:
                    self._resource_semaphores[tag] = Semaphore(t.max_concurrency)

    def _build_graph(self):
        """
        Build:
            - self.tasks_by_name: Dict[name, TaskModel]
            - self.adj: adjacency list keyed by name
            - self.indegree: count of incoming edges keyed by name
        Also validate:
            - unique 'name' values
            - no missing dependencies
            - that each TaskModel.task exists in task_registry
        """
        self.tasks_by_name: Dict[str, TaskModel] = {
            t.name: t for t in self.pipeline.tasks
        }

        # Verify that all names are unique
        if len(self.tasks_by_name) != len(self.pipeline.tasks):
            logger.error("Duplicate task 'name' detected in pipeline.")
            raise ValueError("Duplicate task 'name' detected in pipeline.")

        # Verify that each referenced 'task' maps to a registered function
        missing_tasks: Set[str] = {
            t.task for t in self.pipeline.tasks if t.task not in task_registry
        }
        if missing_tasks:
            logger.error(f"Unknown task(s) in registry: {missing_tasks}")
            raise ValueError(f"Unknown task(s) in registry: {missing_tasks}")

        # Build adjacency & indegree maps
        self.adj: Dict[str, List[str]] = defaultdict(list)
        self.indegree: Dict[str, int] = {name: 0 for name in self.tasks_by_name}

        for t in self.tasks_by_name.values():
            for dep_name in t.depends_on:
                if dep_name not in self.tasks_by_name:
                    logger.error(
                        f"Task '{t.name}' depends on unknown task name '{dep_name}'"
                    )
                    raise ValueError(
                        f"Task '{t.name}' depends on unknown task name '{dep_name}'"
                    )
                self.adj[dep_name].append(t.name)
                self.indegree[t.name] += 1

    def _compute_layers(self) -> List[List[str]]:
        """
        Partition tasks into "layers" (batches) so that all tasks in a layer have
        indegree=0 (i.e. no unfulfilled dependencies), then remove them and repeat.
        This returns a list of lists, where each sublist is a batch of task-names
        that can run concurrently.
        """
        indegree_copy = dict(self.indegree)  # don't modify the original
        adj_copy = {u: list(v) for u, v in self.adj.items()}

        layers: List[List[str]] = []
        remaining = set(self.tasks_by_name.keys())

        while remaining:
            # Find all tasks with indegree == 0
            zero_deps = [n for n in remaining if indegree_copy[n] == 0]
            if not zero_deps:
                # cycle detected
                logger.error("Cycle detected in task dependencies")
                raise RuntimeError("Cycle detected in task dependencies")

            layers.append(zero_deps)
            # Remove these from the graph
            for u in zero_deps:
                remaining.remove(u)
                for v in adj_copy.get(u, []):
                    indegree_copy[v] -= 1

        return layers

    def _render_env(self, raw_env: Dict[str, Any]) -> Dict[str, str]:
        """
        Recursively render each value in raw_env as a Jinja2 template
        and return a flat dict of string->string to inject into os.environ.
        """
        def render_val(v: Any) -> str:
            if isinstance(v, str):
                tmpl = self._jinja_env.from_string(v)
                try:
                    return tmpl.render(**self.context)
                except jinja2.UndefinedError as e:
                    raise RuntimeError(f"Env template error in '{v}': {e}")
            else:
                # Non-string values get cast to str
                return str(v)

        return {k: render_val(v) for k, v in raw_env.items()}

    def _render_params(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively walk raw_params and render any string values as Jinja2 templates
        against self.context. For non-string or nested structures, process accordingly.
        """
        def render_value(value: Any) -> Any:
            if isinstance(value, str):
                # Treat the entire string as a Jinja2 template
                template = self._jinja_env.from_string(value)
                try:
                    return template.render(**self.context)
                except jinja2.UndefinedError as e:
                    raise RuntimeError(f"Template error in '{value}': {e}")
            elif isinstance(value, dict):
                return {k: render_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [render_value(v) for v in value]
            else:
                # int, float, bool, etc.-leave as-is
                return value

        return render_value(raw_params)

    async def _run_single_task(self, name: str) -> None:
        """
        Execute one task by name, honoring:
         - run_if (evaluate a Jinja2 expression; skip if false)
         - retries (number of extra attempts)
         - retry_delay (seconds to sleep between attempts)
         - timeout (max seconds to wait for the underlying awaitable)
         - ignore_failure

        To unify sync vs. async:
        1) If func is a coroutine function, `coro = func(params)`
        2) Else, `coro = loop.run_in_executor(None, func, params)`
        Then we `await coro` (or `await asyncio.wait_for(coro, timeout)`).

        Records summary info (start time, attempts, status, duration, error).
        """
        task_model = self.tasks_by_name[name]
        func = task_registry[task_model.task]

        # ---- 0) SKIP-DOWNSTREAM-ON-FAILURE ----
        # If any dependency declared skip_downstream_on_failure=True and failed,
        # then skip this task.
        for dep in task_model.depends_on:
            dep_model = self.tasks_by_name[dep]
            if dep_model.skip_downstream_on_failure:
                dep_summary = self._summary.tasks.get(dep)
                if dep_summary and dep_summary.status != "success":
                    logger.info(
                        f"Task '{name}' skipped because dependency '{dep}' failed "
                        f"and skip_downstream_on_failure=True."
                    )
                    self._summary.record_skipped(name)
                    self.context[name] = None
                    return

        # ---- 1) CONDITIONAL EXECUTION ----
        # A) run_unless: if provided and truthy -> skip
        if task_model.run_unless:
            tmpl_un = self._jinja_env.from_string(task_model.run_unless)
            val_un = tmpl_un.render(**self.context).strip().lower()
            if val_un in ("true", "1", "yes"):
                logger.info(f"Task '{name}' skipped because run_unless evaluated to '{val_un}'.")
                self._summary.record_skipped(name)
                self.context[name] = None
                return

        # B) run_if: if provided and falsy -> skip
        if task_model.run_if:
            try:
                tmpl_if = self._jinja_env.from_string(task_model.run_if)
                rendered = tmpl_if.render(**self.context)
            except jinja2.UndefinedError as e:
                raise RuntimeError(f"Template error in run_if for '{name}': {e}")

            # Interpret the rendered string as a boolean
            rendered_lower = rendered.strip().lower()
            if rendered_lower not in ("true", "1", "yes"):
                logger.info(f"Task '{name}' skipped because run_if evaluated to '{rendered}'.")
                # Mark skipped in summary and store None in context
                self._summary.record_skipped(name)
                self.context[name] = None

                TASK_STATUS.labels(task=name, status="skipped").inc()
                TASK_DURATION.labels(task=name, status="skipped").observe(0.0)
                return

            # else: run_if is truthy -> proceed to actual execution

        # ---- 2) PARAM RENDERING ----
        try:
            raw_params: Dict[str, Any] = task_model.params or {}
            params = self._render_params(raw_params)
        except Exception as e:
            raise RuntimeError(f"Error rendering params for task '{name}': {e}")

        max_attempts = 1 + (task_model.retries or 0)
        delay = float(task_model.retry_delay or 0.0)
        timeout = task_model.timeout  # None or float
        ignore_failure = bool(task_model.ignore_failure)

        # Prepare execution as an inner coroutine (to allow semaphore)
        async def execute():
            # ---- ENVIRONMENT INJECTION ----
            raw_env = task_model.env or {}
            if raw_env:
                try:
                    env_vars = self._render_env(raw_env)
                except Exception as e:
                    raise RuntimeError(f"Error rendering env for task '{name}': {e}")

                # Save current values
                _old = {k: os.environ.get(k) for k in env_vars}
                # Inject new ones
                os.environ.update(env_vars)
            else:
                env_vars = {}
                _old = {}

            self._summary.record_start(name)

            attempt = 0

            while True:
                attempt += 1
                if asyncio.iscoroutinefunction(func):
                    coro = func(params)
                else:
                    # Offload sync function to a threadpool so it doesn't block the loop
                    loop = asyncio.get_running_loop()
                    coro = loop.run_in_executor(None, func, params)

                try:
                    # capture whatever the task returned
                    start = time.time()
                    if timeout and timeout > 0:
                        result = await asyncio.wait_for(coro, timeout=timeout)
                    else:
                        result = await coro
                    dur = time.time() - start

                    # record metrics
                    TASK_STATUS.labels(
                        pipeline=self.pipeline_name,
                        task=name,
                        status="success"
                    ).inc()
                    TASK_DURATION.labels(
                        pipeline=self.pipeline_name,
                        task=name,
                        status="success"
                    ).observe(dur)

                    # Record success and store result in context
                    logger.info(f"Task '{name}' succeeded on attempt {attempt}/{max_attempts}")
                    self._summary.record_success(name, attempt)

                    # 📦 unpack dict‐returns into context, or bind single value
                    if isinstance(result, dict):
                        for k, v in result.items():
                            if k in self.context:
                                logger.warning(f"Context key {k!r} overwritten by task '{name}'")
                            self.context[k] = v
                    else:
                        self.context[name] = result

                    return
                except asyncio.TimeoutError as te:
                    # Timeout on this attempt
                    if attempt >= max_attempts:
                        msg = f"Task '{name}' timed out after {timeout}s (attempt {attempt}/{max_attempts})"
                        if ignore_failure:
                            logger.error(msg + " — but ignore_failure=True, continuing.")
                            self._summary.record_failed_ignored(name, attempt, te)
                            # record metrics
                            TASK_STATUS.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_ignored"
                            ).inc()
                            TASK_DURATION.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_ignored"
                            ).observe(time.time() - self._summary.tasks[name].start_time)
                            return
                        else:
                            logger.error(msg)
                            self._summary.record_failed_abort(name, attempt, te)
                            TASK_STATUS.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_abort"
                            ).inc()
                            TASK_DURATION.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_abort"
                            ).observe(time.time() - self._summary.tasks[name].start_time)
                            raise RuntimeError(msg)
                    else:
                        # Log a warning and sleep before next attempt
                        logger.warning(
                            f"⏱️ Task '{name}' timed out after {timeout}s "
                            f"(attempt {attempt}/{max_attempts}). Retrying in {delay:.1f}s..."
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)

                except Exception as exc:
                    # Real exception from the task body
                    if attempt >= max_attempts:
                        msg = f"Task '{name}' (func={task_model.task}) failed permanently with: {exc!r}"
                        if task_model.ignore_failure:
                            logger.error(msg + " — but ignore_failure=True, continuing.")
                            self._summary.record_failed_ignored(name, attempt, exc)
                            TASK_STATUS.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_ignored"
                            ).inc()
                            TASK_DURATION.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_ignored"
                            ).observe(time.time() - self._summary.tasks[name].start_time)
                            # Even though failure is ignored, we set context[name] = None
                            self.context[name] = None
                            return
                        else:
                            logger.error(msg)
                            self._summary.record_failed_abort(name, attempt, exc)
                            TASK_STATUS.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_abort"
                            ).inc()
                            TASK_DURATION.labels(
                                pipeline=self.pipeline_name,
                                task=name,
                                status="failed_abort"
                            ).observe(time.time() - self._summary.tasks[name].start_time)
                            raise
                    else:
                        logger.warning(
                            f"⚠️ Task '{name}' (func={task_model.task}) failed with {exc!r} "
                            f"(attempt {attempt}/{max_attempts}). Retrying in {delay:.1f}s..."
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)

                finally:
                    # Restore environment
                    if env_vars:
                        for k, old_val in _old.items():
                            if old_val is None:
                                os.environ.pop(k, None)
                            else:
                                os.environ[k] = old_val

        # Acquire semaphore if resource_tag is set
        sem = None
        tag = task_model.resource_tag
        if tag and tag in self._resource_semaphores:
            sem = self._resource_semaphores[tag]

        if sem:
            async with sem:
                await execute()
        else:
            await execute()

    async def _run_layer(self, names: List[str]) -> None:
        """
        Given a batch of task-names, run them concurrently using asyncio.gather.
        """
        coros = [self._run_single_task(n) for n in names]
        await asyncio.gather(*coros)

    def _topo_sort(self) -> List[str]:
        """
        Kahn's algorithm on self.indegree & self.adj to produce
        a topologically sorted list of 'name' keys. Detects cycles.
        """
        queue = deque([n for n, deg in self.indegree.items() if deg == 0])
        order: List[str] = []

        while queue:
            u = queue.popleft()
            order.append(u)
            for v in self.adj[u]:
                self.indegree[v] -= 1
                if self.indegree[v] == 0:
                    queue.append(v)

        if len(order) != len(self.tasks_by_name):
            raise RuntimeError("Cycle detected in task dependencies")

        return order

    def run(self) -> PipelineRunSummary:
        """
        1. Load all plugins → ensure task_registry is populated
        2. Compute dependency “layers”
        3. For each layer, run all tasks concurrently (with retry logic baked in)
        """
        load_plugins()

        # Re-validate that every TaskModel.task is in registry
        missing = [t.task for t in self.tasks_by_name.values() if t.task not in task_registry]
        if missing:
            logger.error(f"Missing registered functions: {missing}")
            raise RuntimeError(f"Missing registered functions: {missing}")

        logger.info("Starting pipeline execution...")
        layers = self._compute_layers()
        # Run each layer in sequence, but tasks within each layer in parallel
        for layer in layers:
            logger.info(f"Executing layer: {layer}")
            asyncio.run(self._run_layer(layer))

        # Return the summary for further handling (e.g., JSON export)
        return self._summary

    def print_dag(self) -> None:
        """
        ASCII view of each task name and its dependencies.
        """
        for name, t in self.tasks_by_name.items():
            deps = ", ".join(t.depends_on) if t.depends_on else "—"
            logger.info(f"{name:20} depends on → {deps}")

    def to_dot(self) -> str:
        """
        Generate a Graphviz DOT representation of the DAG.
        Each task is a node labeled "<name>\n<task_func>".
        Edges go from each dependency to the dependent.
        """
        lines: List[str] = [
            "digraph NovaPipe {",
            "    rankdir=LR;",  # left-to-right orientation
            "    node [shape=box, style=filled, fillcolor=lightgray];",
            ""
        ]

        # Declare nodes (with label = name + function)
        for name, t in self.tasks_by_name.items():
            label = f"{name}\\n({t.task})"
            lines.append(f'    "{name}" [label="{label}"];')

        lines.append("")  # blank line before edges

        # Declare edges
        for name, t in self.tasks_by_name.items():
            for dep_name in t.depends_on:
                lines.append(f'    "{dep_name}" -> "{name}";')

        lines.append("}")
        return "\n".join(lines)
