# tests/test_cli_describe.py

from click.testing import CliRunner
from novapipe.cli import cli


def test_describe_existing_task():
    runner = CliRunner()
    result = runner.invoke(cli, ["describe", "print_message"])
    assert result.exit_code == 0
    assert "print_message" in result.output
    assert "prints the \"message\" field" in result.output


def test_describe_missing_task():
    runner = CliRunner()
    result = runner.invoke(cli, ["describe", "no_such_task"])
    assert result.exit_code != 0
    assert "not found" in result.output
