import yaml
import pytest
from click.testing import CliRunner
import logging

from novapipe.cli import cli


def test_global_ignore_failures(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    # Pipeline: first task always fails (no ignore_failure in YAML),
    # second depends on it.
    pipeline = """
    tasks:
      - name: fail
        task: always_fail

      - name: next
        task: print_message
        params:
          message: "Should run despite failure"
        depends_on:
          - fail
    """
    (tmp_path / "pipeline.yaml").write_text(pipeline)

    # Run without --ignore-failures → should abort
    runner = CliRunner()
    result = runner.invoke(cli, ["run", str(tmp_path/"pipeline.yaml")])
    assert result.exit_code != 0
    assert "❌ Pipeline failed" in result.output

    # Run with --ignore-failures → exit code 0 and second task runs
    result2 = runner.invoke(
        cli,
        ["run", str(tmp_path/"pipeline.yaml"), "--ignore-failures"]
    )
    assert result2.exit_code == 0
    assert "Should run despite failure" in result2.output
