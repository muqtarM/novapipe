import os
import shutil
import click
import yaml
import inspect as _inspect
import asyncio
import logging

from .runner import PipelineRunner
from .tasks import task_registry, load_plugins
from .logging_conf import configure_logging
# try:
#     # Python 3.8+
#     from importlib.metadata import distributions
# except ImportError:
#     # back-port for older versions
from importlib_metadata import distributions


@click.group()
@click.version_option("0.1.0", package_name="novapipe", prog_name="novapipe")
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Enable DEBUG logging for NovaPipe."
)
def cli(verbose) -> None:
    """
     NovaPipe — lightweight, plugin-driven ETL orchestration.
     """
    level = "DEBUG" if verbose else "INFO"
    configure_logging(level=level)


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
@click.option(
    "--var", "-D",
    "vars",
    metavar="KEY=VAL",
    multiple=True,
    help="Set a pipeline variable (can be used multiple times).",
)
@click.option(
    "--summary-json",
    "summary_path",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Path to write task summary JSON after run"
)
@click.option(
    "--metrics-port",
    type=int,
    default=None,
    help="If set, start a Prometheus metrics server on this port.",
)
def run(pipeline_file: str, vars: list, summary_path: str, metrics_port: int) -> None:
    """Run a pipeline YAML file."""
    with open(pipeline_file) as f:
        data = yaml.safe_load(f)

    load_plugins()
    runner = PipelineRunner(data)

    # Parse CLI vars and seed runner.context
    for var_pair in vars:
        if "=" not in var_pair:
            click.echo(f"❌ Invalid --var format: {var_pair!r}. Use KEY=VAL.", err=True)
            raise SystemExit(1)
        key, val = var_pair.split("=", 1)
        runner.context[key] = val

    if metrics_port:
        from prometheus_client import start_http_server
        start_http_server(metrics_port)
        click.echo(f"📊 Metrics available at http://localhost:{metrics_port}/metrics")

    try:
        summary = runner.run()  # now returns PipelineRunSummary, with seeded context used in templates
        click.echo("✅ Pipeline completed (check logs for details).")

        if summary_path:
            # Write JSON summary to disk
            import json

            out = {"tasks": summary.to_list()}
            with open(summary_path, "w") as jf:
                json.dump(out, jf, indent=2)
            click.echo(f"📝 Summary written to {summary_path}")
    except Exception as e:
        click.echo(f"❌ Pipeline failed: {e}", err=True)
        raise SystemExit(1)


@cli.command()
def inspect() -> None:
    """List all registered tasks."""
    load_plugins()
    click.echo("Registered tasks:")
    for name, func in sorted(task_registry.items()):
        sig = _inspect.signature(func)
        click.echo(f"- {name}{sig}")


@cli.command("describe")
@click.argument("task_name")
def describe(task_name: str):
    """
    Show the full signature and docstring of a given task.
    """
    load_plugins()
    func = task_registry.get(task_name)
    if not func:
        click.echo(f"❌ Task {task_name!r} not found.", err=True)
        raise SystemExit(1)

    # ---- Gather plugin metadata ----
    plugin_info = {}
    for dist in distributions():
        for ep in dist.entry_points:
            if ep.group == "novapipe.plugins":
                module_name = ep.value
                # Load the plugin module and scan for tasks
                try:
                    mod = __import__(module_name, fromlist=["*"])
                except ImportError:
                    continue
                for fname, fobj in vars(mod).items():
                    if callable(fobj) and getattr(fobj, "__wrapped__", None):
                        # decorated with @task
                        plugin_info[fname] = {
                            "distribution": dist.metadata.get("Name", dist.name),
                            "version": dist.version,
                        }

    # Signature
    sig = _inspect.signature(func)
    click.echo(f"{task_name}{sig}\n")

    # Docstring (or placeholder)
    doc = _inspect.getdoc(func) or "(no documentation provided)"
    click.echo(doc)

    # If this is a plugin task, show where it came from
    info = plugin_info.get(task_name)
    if info:
        click.echo()
        click.echo("Plugin Metadata:")
        click.echo(f" • Distribution: {info['distribution']} (v{info['version']})")
        click.echo(f" • Module:       {func.__module__}")


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


@plugin.command("list")
def plugin_list():
    """
    List all installed NovaPipe plugins (distribution, version, module, tasks).
    """
    load_plugins()
    # Gather plugins by distribution
    plugins = {}
    for dist in distributions():
        name = dist.metadata.get("Name", dist.name)
        version = dist.version
        for ep in dist.entry_points:
            if ep.group == "novapipe.plugins":
                # ep.name is the entry-point alias (i.e. the task name)
                task_name = ep.name
                module = ep.value
                key = f"{name} (v{version})"
                plugins.setdefault(key, []).append((task_name, module))

    if not plugins:
        click.echo("No NovaPipe plugins installed.")
        return

    click.echo("Installed NovaPipe plugins:")
    for dist_key, tasks in sorted(plugins.items()):
        click.echo(f"\n• {dist_key}")
        for task_name, module in sorted(tasks):
            click.echo(f"    – {task_name}  (module: {module})")


@cli.command("dag")
@click.argument("pipeline_file", type=click.Path(exists=True))
@click.option(
    "--dot",
    "export_dot",
    is_flag=True,
    default=False,
    help="Output Graphviz DOT instead of ASCII.",
)
def dag(pipeline_file, export_dot):
    """
    Show task-dependency graph for a pipeline.
    By default, prints an ASCII view. Use --dot to emit Graphviz DOT.
    """
    import yaml

    with open(pipeline_file) as f:
        data = yaml.safe_load(f)

    # Initialize runner (validates & builds graph)
    runner = PipelineRunner(data)

    if export_dot:
        dot_text = runner.to_dot()
        click.echo(dot_text)
    else:
        click.echo("🚀 NovaPipe DAG:")
        runner.print_dag()


if __name__ == '__main__':
    cli(prog_name="novapipe")
