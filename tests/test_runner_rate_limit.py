import time
import yaml
import pytest

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# A dummy task that records invocation timestamp
@task
def record_time(params):
    return time.monotonic()


def test_rate_limit(tmp_path):
    # Two tasks in the same layer sharing a rate of 1 call/sec
    pipeline = """
    tasks:
      - name: t1
        task: record_time
        rate_limit: 1
        rate_limit_key: "group"

      - name: t2
        task: record_time
        rate_limit: 1
        rate_limit_key: "group"
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data, pipeline_name="rl_test")
    summary = runner.run()

    # The two timestamps should be at least ~1 second apart
    t1, t2 = runner.context["t1"], runner.context["t2"]
    assert abs(t2 - t1) >= 0.9  # allow small scheduling jitter
