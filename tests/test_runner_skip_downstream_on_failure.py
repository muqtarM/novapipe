import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# A task that always fails
@task
def always_fail(params):
    raise RuntimeError("boom")


# A simple pass‐through
@task
def identity(params):
    return params.get("x", None)


def test_skip_children_of_failed_task(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = """
    tasks:
      - name: fail_task
        task: always_fail
        ignore_failure: true
        skip_downstream_on_failure: true

      - name: child_task
        task: identity
        params:
          x: "should_be_skipped"
        depends_on:
          - fail_task

      - name: grandchild
        task: identity
        params:
          x: "{{ child_task }}"
        depends_on:
          - child_task
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    stats = {t["name"]: t for t in summary.to_list()}

    # Parent failed but was ignored
    assert stats["fail_task"]["status"] == "failed_ignored"
    # Child skipped because of skip_downstream_on_failure
    assert stats["child_task"]["status"] == "skipped"
    # Grandchild also skipped (since its dependency 'child_task' was skipped)
    assert stats["grandchild"]["status"] == "skipped"

    # Check logs
    assert any(
        "skipped because dependency 'fail_task' failed" in rec.message
        for rec in caplog.records
    )
