# tests/test_cli_playground.py

import json
from click.testing import CliRunner
from novapipe.cli import cli


def test_playground_oneoff_numbers():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["playground", "-D", "x=5", "-D", "y=7", "{{ x*y }}"],
    )
    assert result.exit_code == 0
    assert "35" in result.output


def test_playground_invalid_var():
    runner = CliRunner()
    result = runner.invoke(cli, ["playground", "-D", "badformat", "{{ 1 }}"])
    assert result.exit_code == 0
    assert "Invalid var" in result.output
