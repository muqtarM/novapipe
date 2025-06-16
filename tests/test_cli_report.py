import json
from click.testing import CliRunner

from novapipe.cli import cli


def test_report_simple(tmp_path):
    summary = {
        "tasks": [
            {"name": "a", "status": "success", "attempts": 1, "duration_secs": 0.01, "error": None},
            {"name": "b", "status": "failed_abort", "attempts": 2, "duration_secs": 0.05, "error": "Boom"},
        ]
    }
    p = tmp_path / "sum.json"
    p.write_text(json.dumps(summary))
    runner = CliRunner()
    result = runner.invoke(cli, ["report", str(p)])
    assert result.exit_code == 0
    out = result.output
    assert "a" in out and "success" in out
    assert "b" in out and "failed_abort" in out
