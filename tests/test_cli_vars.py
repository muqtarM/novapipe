# tests/test_cli_vars.py

import yaml
from click.testing import CliRunner
import json

from novapipe.cli import cli


def test_cli_var_injection(tmp_path):
    # Write a simple pipeline that echoes a CLI var
    pipeline = """
    tasks:
      - name: echo_var
        task: print_message
        params:
          message: "VAR={{ myvar }}"
    """
    (tmp_path / "pipeline.yaml").write_text(pipeline)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run",
            str(tmp_path / "pipeline.yaml"),
            "--var", "myvar=hello_there"
        ],
        catch_exceptions=False
    )
    # Expect it to run without errors and print the expanded var
    assert result.exit_code == 0
    assert "VAR=hello_there" in result.output
