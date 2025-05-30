import logging
import inspect
import asyncio
from .tasks import TASKS, load_plugins
from .models import Pipeline


class PipelineRunner:
    """
    Executes a validated Pipeline of Steps, supporting async tasks.
    """
    def __init__(self, pipeline_def: dict) -> None:
        load_plugins()
        # Validate and parse pipeline definition
        pipeline = Pipeline.model_validate(pipeline_def)
        self.steps = pipeline.tasks

    def run_step(self, fn: callable, params: dict) -> None:
        if inspect.iscoroutinefunction(fn):
            asyncio.run(fn(**params))
        else:
            fn(**params)

    def run(self) -> None:
        for idx, step in enumerate(self.steps, start=1):
            logging.info(f"[Step {idx}] {step.name} -> {step.task}({step.params})")
            fn = TASKS.get(step.task)
            if not fn:
                available = ', '.join(TASKS.keys())
                raise ValueError(f"Task '{step.task}' not found. Available: {available}")
            try:
                self.run_step(fn, step.params)
            except TypeError as e:
                raise RuntimeError(f"Error in task '{step.task}': {e}")
