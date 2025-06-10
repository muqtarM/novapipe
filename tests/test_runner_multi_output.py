# tests/test_runner_multi_output.py

import yaml
import pytest

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# A task that returns multiple outputs
@task
def multi(params):
    return {
        "a": params.get("x", 1) * 2,
        "b": params.get("y", 3) + 5,
    }


# A consumer that reads them
@task
def consume(params):
    # echo out the values for assertion
    return f"A is {params['a']}, B is {params['b']}"


def test_multi_output_binding(tmp_path):
    pipeline = """
    tasks:
      - name: step1
        task: multi
        params:
          x: 4
          y: 7

      - name: step2
        task: consume
        params:
          a: "{{ a }}"
          b: "{{ b }}"
        depends_on:
          - step1
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    # verify context
    assert runner.context["a"] == 8
    assert runner.context["b"] == 12

    # verify the consume task's return was bound under its name
    assert runner.context["step2"] == "A is 8, B is 12"

    # summary statuses
    stats = {t["name"]: t for t in summary.to_list()}
    assert stats["step1"]["status"] == "success"
    assert stats["step2"]["status"] == "success"
