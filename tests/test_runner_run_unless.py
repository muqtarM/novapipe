import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# Minimal tasks
@task
def return_value(params):
    return params.get("value")


@task
def echo(params):
    msg = params.get("message", "")
    print(msg)
    return msg


def test_run_unless_skips_when_true(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = """
    tasks:
      - name: always
        task: return_value
        params:
          value: 42

      - name: skip_if_unless
        task: echo
        params:
          message: "Should be skipped"
        run_unless: "{{ always == 42 }}"
        depends_on:
          - always

      - name: downstream
        task: echo
        params:
          message: "Still runs"
        depends_on:
          - skip_if_unless
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    stats = {t["name"]: t for t in summary.to_list()}
    assert stats["skip_if_unless"]["status"] == "skipped"
    assert stats["skip_if_unless"]["attempts"] == 0
    assert stats["downstream"]["status"] == "success"

    # Check log
    assert any("skipped because run_unless" in rec.message for rec in caplog.records)


def test_run_unless_allows_when_false(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = """
    tasks:
      - name: always
        task: return_value
        params:
          value: 99

      - name: dont_skip
        task: echo
        params:
          message: "Should run"
        run_unless: "{{ always == 42 }}"
        depends_on:
          - always
    """
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data)
    summary = runner.run()

    stats = {t["name"]: t for t in summary.to_list()}
    assert stats["dont_skip"]["status"] == "success"
    assert stats["dont_skip"]["attempts"] == 1
