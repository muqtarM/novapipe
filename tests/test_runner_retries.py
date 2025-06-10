# tests/test_runner_retries.py

import asyncio
import yaml
from novapipe.runner import PipelineRunner
from novapipe.tasks import task, task_registry

# A counter to track how many times our dummy function has been called
_CALL_COUNT = {"count": 0}


@task
def fail_twice(params):
    """
    A sync task that raises the first two times, then prints success.
    """
    _CALL_COUNT["count"] += 1
    if _CALL_COUNT["count"] < 3:
        raise RuntimeError("Intentional fail")
    print("Recovered on attempt 3!")


async def test_retries(tmp_path, capsys):
    pipeline_str = """
    tasks:
      - name: flaky
        task: fail_twice
        retries: 2
        retry_delay: 0.1
    """
    data = yaml.safe_load(pipeline_str)
    runner = PipelineRunner(data)

    # Run the pipeline; since retries=2, total attempts=3 → our function recovers on 3rd try
    runner.run()

    captured = capsys.readouterr()
    assert "Recovered on attempt 3!" in captured.out
    # Ensure the function was indeed called 3 times
    assert _CALL_COUNT["count"] == 3
