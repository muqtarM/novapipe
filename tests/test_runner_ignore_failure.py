# tests/test_runner_ignore_failure.py

import random
import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task, task_registry


# A task that always raises
@task
def always_fail(params):
    raise RuntimeError("Intentional fail")


def test_ignore_failure(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger="novapipe")

    pipeline_str = """
    tasks:
      - name: fail_but_ignore
        task: always_fail
        retries: 0
        ignore_failure: true

      - name: next_step
        task: print_message
        params:
          message: "Should run despite previous failure"
        depends_on:
          - fail_but_ignore
    """
    data = yaml.safe_load(pipeline_str)
    runner = PipelineRunner(data)

    # Should not raise, because ignore_failure=True
    runner.run()

    # Check that we saw a warning about ignoring failure
    found = any(
        "failed permanently" in rec.message and "ignore_failure=True" in rec.message
        for rec in caplog.records
    )
    assert found, "Expected a warning about ignored failure"

    # Check summary warning at end
    summary_warning = any(
        "failed but were ignored" in rec.message for rec in caplog.records
    )
    assert summary_warning, "Expected a summary warning listing ignored tasks"
