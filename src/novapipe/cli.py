import os
import shutil
import click
import yaml
import inspect
import asyncio
import logging

from .runner import PipelineRunner
from .tasks import TASKS, load_plugins


@click.group()
@click.version_option("0.1.0", package_name="novapipe", prog_name="novapipe")
def cli() -> None:
    """NovaPipe: Advanced plugin-driven ETL CLI."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


@cli.command()
@click.argument("name", required=False, default="pipeline.yaml")
def init(name) -> None:
    """
    Create a started pipeline YAML file.
    """
    template = """\
# NovaPipe pipeline template

tasks:
    - name: print_message
      params:
        message: "Hello, NovaPipe!
    """
    if os.path.exists(name):
        click.echo(f"!  {name} already exists. Aborting.")
        raise SystemExit(1)

    with open(name, 'w') as f:
        f.write(template)
    click.echo(f"Initialized pipeline template at {name}")


@cli.command()
@click.argument("pipeline_file", type=click.Path(exists=True))
def run(pipeline_file: str) -> None:
    """Run a pipeline YAML file."""
    with open(pipeline_file) as f:
        data = yaml.safe_load(f)

    # dynamic plugin loading
    load_plugins()

    runner = PipelineRunner(data)
    try:
        runner.run()  # automatically handles async tasks
        click.secho("Pipeline completed successfully.", fg="green")
    except Exception as e:
        click.echo(f"Pipeline failed: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def inspect() -> None:
    """List all registered tasks."""
    load_plugins()
    click.echo("Registered tasks:")
    for name in sorted(TASKS.keys()):
        func = TASKS[name]
        sig = inspect.signature(func)
        click.echo(f"- {name}{sig}")


@cli.group()
def plugin():
    """
    Plugin management commands.
    """
    pass


@plugin.command("scaffold")
@click.argument("plugin_name")
def plugin_scaffold(plugin_name: str) -> None:
    """
    Scaffold a new NovaPipe plugin project.
    """
    # e.g. plugin_name = "novapipe foo"
    project_dir = os.path.abspath(plugin_name)
    if os.path.exists(project_dir):
        click.echo(f"! Directory {project_dir} already exists. Aborting.")
        raise SystemExit(1)

    # create structure
    os.makedirs(os.path.join(project_dir, plugin_name))
    with open(os.path.join(project_dir, "pyproject.toml"), "w") as f:
        f.write(f"""\
[tool.poetry]
name = "{plugin_name}"
version = "0.1.0"
description = "A NovaPipe plugin providing additional tasks."
authors = ["<you@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
novapipe = "^0.1.0"

[tool.poetry.plugins."novapipe.plugins"]
{plugin_name} = "{plugin_name}.tasks"
""")

    with open(os.path.join(project_dir, plugin_name, "__init__.py"), "w") as f:
        f.write("# Plugin package for NovaPipe\n")

    with open(os.path.join(project_dir, plugin_name, "tasks.py"), "w") as f:
        f.write(f"""\
from novapipe.tasks import task

@task
def hello_{plugin_name}(params: dict):
    \"""
    Sample task for the {plugin_name} plugin.
    \"""
    print("Hello from {plugin_name}!", params)
""")

    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(f"# {plugin_name}\n\nA NovaPipe plugin scaffold by `novapipe plugin scaffold {plugin_name}`.\n")

    click.echo(f"✅ Scaffolded new plugin at {project_dir}")
    click.echo("👉 Next steps:")
    click.echo(f"   • cd {plugin_name}")
    click.echo("   • poetry install")
    click.echo("   • Implement your tasks in tasks.py")
    click.echo("   • git init && git add . && git commit -m 'Initial plugin scaffold'")


if __name__ == '__main__':
    cli()
