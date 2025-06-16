from __future__ import annotations

import logging
import os
import sys
import importlib
import tempfile
from importlib_metadata import distributions, EntryPoint
from typing import Callable, Dict, Any
import random

# Global registry of tasks
task_registry: Dict[str, Callable[[dict], None]] = {}

# global pins: dist_name -> version
_plugin_pins: Dict[str, str] = {}


def set_plugin_pins(pins: Dict[str, str]) -> None:
    """
    pins: mapping of distribution name -> version to pin for that plugin.
    Example: {'novapipe-foo': '0.2.1'}
    """
    global _plugin_pins
    _plugin_pins = pins


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

    # Gather all (dist_name, dist_version, entry_point) tuples
    ep_map: Dict[str, list[tuple[str, str, EntryPoint]]] = {}
    for dist in distributions():
        dist_name = dist.metadata.get("Name", dist.name)
        dist_version = dist.version
        for ep in dist.entry_points:
            if ep.group == "novapipe.plugins":
                ep_map.setdefault(ep.name, []).append((dist_name, dist_version, ep))

    # Resolve and register
    errors: list[str] = []
    for task_name, candidates in ep_map.items():
        if len(candidates) == 1:
            dist_name, dist_version, ep = candidates[0]
        else:
            # multiple candidates -> need pin
            # find matches among candidates
            matched = [
                (d, v, e) for (d, v, e) in candidates
                if _plugin_pins.get(d) == v
            ]
            if len(matched) == 1:
                dist_name, dist_version, ep = matched[0]
            else:
                # build a helpful error message
                opts = ", ".join(f"{d}=={v}" for d, v, _ in candidates)
                errors.append(
                    f"Task '{task_name}' is provided by multiple plugins: {opts}. "
                    f"Pin one with --plugin-version DIST==VERSION."
                )
                continue

        # load and register
        func = ep.load()
        if task_name in task_registry:
            # overriding a built-in or earlier plugin; warn or allow if pinned
            logging.getLogger("novapipe").warning(
                f"Task '{task_name}' from plugin {dist_name}=={dist_version} "
                f"is overriding existing registration"
            )
        task_registry[task_name] = func

    if errors:
        raise RuntimeError("Plugin load errors:\n  " + "\n  ".join(errors))


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
