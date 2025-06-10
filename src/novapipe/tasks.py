from __future__ import annotations

import os
import sys
import importlib
import tempfile
from typing import Callable, Dict, Any
import random

# Global registry of tasks
task_registry: Dict[str, Callable[[dict], None]] = {}


def task(func: Callable[[dict], None]) -> Callable[[dict], None]:
    """
    Decorator to register a function (sync or async) as a NovaPipe task.
    Usage:
    @task()
    def my_task(param1, param2):
        ...
    """
    task_registry[func.__name__] = func
    return func


def load_plugins() -> None:
    """
    Discover and load external plugins via entry point group 'novapipe.plugins'.
    Plugins should define entry_points in their own pyproject.
    """
    try:
        # Python 3.8+ stdlib
        from importlib.metadata import entry_points
    except ImportError:
        # Older Python / importlib_metadata back-compat
        from importlib_metadata import entry_points

    # Try the new API: entry_points(group=...)
    try:
        eps = entry_points(group="novapipe.plugins")
    except TypeError:
        # Fallback for older importlib.metadata that returns a dict
        all_eps = entry_points()
        eps = all_eps.get("novapipe.plugins", [])

    for ep in eps:
        module_name = ep.value if hasattr(ep, "value") else ep.module  # e.g. "novapipe_foo.tasks"
        if module_name in sys.modules:
            continue
        importlib.import_module(module_name)


# ──────────────── Built-in Tasks ────────────────

@task
def print_message(params: Dict) -> None:
    """
    A simple built-in task that prints the "message" field from params.
    Example usage in pipeline.yaml:

    tasks:
      - name: say_hello
        task: print_message
        params:
          message: "Hello, NovaPipe!"
    """
    msg = params.get("message", "")
    print(msg)


@task
async def async_wait_and_print(params: Dict) -> None:
    """
    An example async task that waits N seconds, then prints a message.
    Pipeline usage:

    tasks:
      - name: delayed
        task: async_wait_and_print
        params:
          message: "This ran after waiting"
          seconds: 2
    """
    seconds = params.get("seconds", 1)
    message = params.get("message", "")
    # Simple asyncio sleep
    import asyncio

    await asyncio.sleep(seconds)
    print(message)


@task
def maybe_fail(params: Dict) -> None:
    """
    A demo task that randomly raises to simulate flakiness.
    """
    attempt_id = params.get("attempt_id", None)
    if random.random() < 0.5:  # 50% chance to fail
        raise RuntimeError(f"Simulated failure for attempt_id={attempt_id}")
    print(f"✅ maybe_fail succeeded (attempt_id={attempt_id})")


@task
def create_temp_dir(params: Dict) -> str:
    """
    Create a unique temporary directory under `base`. Return its path.
    """
    base = params.get("base", None)
    if base and not os.path.isdir(base):
        raise RuntimeError(f"Base directory {base!r} does not exist.")
    tmpdir = tempfile.mkdtemp(prefix="novapipe_", dir=base)
    return tmpdir


@task
def write_text_file(params: Dict) -> str:
    """
    Create a text file at `path` with content `content`. Return the file path.
    """
    path = params.get("path")
    content = params.get("content", "")
    if not path:
        raise RuntimeError("Missing 'path' in params for write_text_file.")
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


@task
def count_file_lines(params: Dict) -> int:
    """
    Count the number of lines in the file at `path`. Return the integer count.
    """
    path = params.get("path")
    if not path or not os.path.isfile(path):
        raise RuntimeError(f"File not found: {path!r}")
    with open(path) as f:
        return sum(1 for _ in f)


@task
def return_value(params: Dict) -> Any:
    """
    Return whatever is in params['value'].
    """
    return params.get("value")


@task
def wrap_text(params: Dict) -> str:
    """
    Return 'WRAPPED: <input!r>' where input = params['input'].
    """
    inp = params.get("input", "")
    return f"WRAPPED: {inp!r}"


@task
def echo(params: Dict) -> Any:
    """
    Print and return params['message'].
    """
    msg = params.get("message", "")
    print(msg)
    return msg


@task
def analyze_data(params):
    # returns a dict of multiple useful stats
    return {
      "row_count": 123,
      "column_count": 10,
      "output_path": "/tmp/novapipe_out.csv",
    }
