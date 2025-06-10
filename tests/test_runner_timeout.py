# tests/test_runner_timeout.py

import asyncio
import yaml
import pytest

from novapipe.runner import PipelineRunner
from novapipe.tasks import task, task_registry

@task
async def always_sleep(params):
    """
    Never-ending sleep—will always exceed any reasonable timeout.
    """
    await asyncio.sleep(10)
    print("You should never see this line.")


def test_timeout_raises(tmp_path):
    # Define a pipeline where always_sleep has timeout=0.1 and no retries
    pipeline_str = """
    tasks:
      - name: infinite
        task: always_sleep
        timeout: 0.1
        retries: 0
    """
    data = yaml.safe_load(pipeline_str)
    runner = PipelineRunner(data)

    with pytest.raises(RuntimeError) as excinfo:
        runner.run()

    # Ensure our exception message mentions “timed out”
    assert "timed out" in str(excinfo.value)
