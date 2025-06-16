import os
import yaml
import pytest

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# A task that reads an env var and returns it
@task
def echo_env(params):
    key = params["key"]
    return os.environ.get(key)


def test_env_injection(tmp_path):
    # Pipeline that injects FOO=bar and then reads it
    pipeline = """
    tasks:
      - name: test_env
        task: echo_env
        env:
          FOO: "bar"
        params:
          key: "FOO"
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data, pipeline_name="test")
    summary = runner.run()

    # Confirm context got the env var return
    assert runner.context["test_env"] == "bar"

    # And that after run, FOO is not left in os.environ
    assert os.environ.get("FOO") is None
