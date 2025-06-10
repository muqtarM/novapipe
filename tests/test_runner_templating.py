# tests/test_runner_templating.py

import os
import yaml
import tempfile
import pytest
import logging
import json

from novapipe.runner import PipelineRunner
from novapipe.tasks import task, task_registry

# Register built-in tasks for this test
@task
def return_value(params):
    # Simply return the 'value' param
    return params.get("value")

@task
def wrap_text(params):
    # Return "WRAPPED: " + input
    inp = params.get("input", "")
    return f"WRAPPED: {inp!r}"

@task
def echo(params):
    # Return back the message
    msg = params.get("message", "")
    print(msg)
    return msg

def test_templating_between_tasks(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline_str = """
    tasks:
      - name: one
        task: return_value
        params:
          value: "hello"

      - name: two
        task: wrap_text
        params:
          input: "{{ one }}"
        depends_on:
          - one

      - name: three
        task: echo
        params:
          message: "{{ two }} + world"
        depends_on:
          - two
    """
    (tmp_path / "pipeline.yaml").write_text(pipeline_str)
    summary_file = tmp_path / "summary.json"

    # Run NovaPipe with summary output
    runner = PipelineRunner(yaml.safe_load(pipeline_str))
    summary = runner.run()

    # Check that context was populated correctly
    # task "one" should have returned "hello"
    assert runner.context["one"] == "hello"
    # task "two" should see "hello" and return something like "WRAPPED: 'hello'"
    assert runner.context["two"].startswith("WRAPPED")
    # templated message in "three" should be f"{runner.context['two']} + world"
    expected_msg = f"{runner.context['two']} + world"
    assert runner.context["three"] == expected_msg

    # Finally, write and read the summary JSON
    with open(summary_file, "w") as jf:
        json.dump({"tasks": summary.to_list()}, jf, indent=2)
    data = json.loads(summary_file.read_text())
    assert len(data["tasks"]) == 3
    names = {t["name"]: t for t in data["tasks"]}
    assert names["one"]["status"] == "success"
    assert names["two"]["status"] == "success"
    assert names["three"]["status"] == "success"
