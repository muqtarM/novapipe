from __future__ import annotations

import importlib.metadata
import logging

# Global registry of tasks
TASKS: dict[str, callable] = {}


def task(name: str | None = None):
    """
    Decorator to register a function (sync or async) as a NovaPipe task.
    Usage:
    @task()
    def my_task(param1, param2):
        ...
    """
    def decorator(fn: callable) -> callable:
        task_name = name or fn.__name__
        TASKS[task_name] = fn
        logging.debug(f"Registered task '{task_name}' from {fn.__module__}")
        return fn
    return decorator


def load_plugins() -> None:
    """
    Discover and load external plugins via entry point group 'novapipe.plugins'.
    Plugins should define entry_points in their own pyproject.
    """
    for entry in importlib.metadata.entry_points().get('novapipe.plugins', []):
        try:
            entry.load()
            logging.info(f"Loaded plugin: {entry.name}")
        except Exception as e:
            logging.warning(f"Failed to load plugin {entry.name}: {e}")


# Example sync task
task()(lambda message: print(message))


# Example async task
@task()
async def async_wait_and_print(message: str, delay: int = 1) -> None:
    import asyncio
    await asyncio.sleep(delay)
    print(message)
