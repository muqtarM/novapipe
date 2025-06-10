# tests/test_runner_run_if.py

import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# Register minimal tasks for testing
@task
def return_value(params):
    return params.get("value")


@task
def print_message(params):
    # Print the message so we can see it in the logs, but return it for the context
    msg = params.get("message", "")
    print(msg)
    return msg


def test_run_if_true(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = """
    tasks:
      - name: one
        task: return_value
        params:
          value: 10

      - name: cond
        task: return_value
        params:
          value: "{{ one > 5 }}"
        depends_on:
          - one

      - name: run_this
        task: print_message
        params:
          message: "Ran because one > 5"
        run_if: "{{ cond }}"
        depends_on:
          - cond

      - name: other_task
        task: print_message
        params:
          message: "Always run"
        depends_on:
          - one
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    # "run_this" must have status "success"
    sr = {t["name"]: t for t in summary.to_list()}
    assert sr["run_this"]["status"] == "success"
    assert sr["run_this"]["attempts"] == 1

    # "other_task" always runs
    assert sr["other_task"]["status"] == "success"


def test_run_if_false_skipped(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = """
    tasks:
      - name: one
        task: return_value
        params:
          value: 2

      - name: cond
        task: return_value
        params:
          value: "{{ one > 5 }}"
        depends_on:
          - one

      - name: skip_this
        task: print_message
        params:
          message: "This should be skipped"
        run_if: "{{ cond }}"
        depends_on:
          - cond

      - name: always_run
        task: print_message
        params:
          message: "Always run"
        depends_on:
          - one
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    sr = {t["name"]: t for t in summary.to_list()}
    # "skip_this" must be skipped
    assert sr["skip_this"]["status"] == "skipped"
    assert sr["skip_this"]["attempts"] == 0

    # "always_run" still runs
    assert sr["always_run"]["status"] == "success"

    # Also check that logs contain the skip message
    found = any(
        "skipped because run_if evaluated to" in rec.message
        for rec in caplog.records
    )
    assert found, "Expected an INFO log about skipping"
