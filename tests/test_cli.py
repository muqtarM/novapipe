import pytest
from click.testing import CliRunner
from novapipe.cli import cli
from novapipe.tasks import task
import tempfile, yaml


@task(name='cli_test')
def cli_fn():
    print('CLI OK')


def test_inspect_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['inspect'])
    assert 'cli_test' in result.output


def test_run_command(tmp_path):
    runner = CliRunner()
    pipeline = {'tasks': [{'name': 'check', 'task': 'cli_test'}]}
    file = tmp_path / 'pipe.yaml'
    file.write_text(yaml.dump(pipeline))
    result = runner.invoke(cli, ['run', str(file)])
    assert 'CLI OK' in result.output
    assert 'Pipeline execution complete.' in result.output
