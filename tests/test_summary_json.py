# tests/test_summary_json.py

import yaml
import json
import tempfile
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task
from novapipe.cli import run as novapipe_run


@task
def always_fail(params):
    raise RuntimeError("Boom!")


@task
def greet(params):
    print("Hello!")


def test_summary_json(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline_str = """
    tasks:
      - name: greet
        task: greet
      - name: fail_ignore
        task: always_fail
        retries: 0
        ignore_failure: true
      - name: end
        task: greet
        depends_on:
          - fail_ignore
    """
    (tmp_path / "pipeline.yaml").write_text(pipeline_str)
    summary_file = tmp_path / "summary.json"

    # Simulate CLI invocation
    args = ["pipeline.yaml", "--summary-json", str(summary_file)]
    # Note: click.testing.CliRunner could also be used; here we'll call function directly
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="novapipe"):
        runner = PipelineRunner(yaml.safe_load(pipeline_str))
        summary = runner.run()
        # Explicitly write summary
        with open(summary_file, "w") as f:
            json.dump({"tasks": summary.to_list()}, f)

    # Load and assert content
    data = json.loads(summary_file.read_text())
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) == 3

    # Find the fail_ignore entry
    fi = next(t for t in data["tasks"] if t["name"] == "fail_ignore")
    assert fi["status"] == "failed_ignored"
    assert fi["attempts"] == 1
    assert "RuntimeError('Boom!')" in fi["error"]

    # Greet tasks should be success
    for name in ("greet", "end"):
        t = next(t for t in data["tasks"] if t["name"] == name)
        assert t["status"] == "success"
        assert t["attempts"] == 1
        assert t["error"] is None
