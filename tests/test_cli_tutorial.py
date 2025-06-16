from click.testing import CliRunner
import textwrap

from novapipe.cli import cli


def test_tutorial_skeleton():
    runner = CliRunner()
    # assume 'print_message' has no Example: block
    result = runner.invoke(cli, ["tutorial", "print_message"])
    assert result.exit_code == 0
    out = result.output
    assert "tasks:" in out
    assert "task: print_message" in out


def test_tutorial_from_docstring(tmp_path):
    # Create a dummy plugin with an Example in its doc
    # Register it manually here…
    from novapipe.tasks import task, task_registry
    @task
    def foo(params):
        """
        Does foo.
        Example:
            tasks:
              - name: foo_run
                task: foo
                params:
                  x: 1
        """
        pass

    runner = CliRunner()
    result = runner.invoke(cli, ["tutorial", "foo"])
    assert result.exit_code == 0
    out = result.output
    assert "name: foo_run" in out
    assert "task: foo" in out
