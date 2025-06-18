import json
import os
import shutil
import time
import re
import textwrap

import click
import jinja2
import yaml
from pathlib import Path
import inspect as _inspect
import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .runner import PipelineRunner, PIPELINE_STATUS, PIPELINE_DURATION
from .tasks import task_registry, load_plugins
from .tasks import set_plugin_pins
from .logging_conf import configure_logging
from typing import List, Dict, Any
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
@click.option(
    "--metrics-path", "-p",
    type=str,
    default="/metrics",
    show_default=True,
    help="HTTP path under which to expose metrics.",
)
@click.option(
    "--ignore-failures",
    is_flag=True,
    default=False,
    help="Globally treat all tasks as ignore_failure=True (unless overridden per-task).",
)
@click.option(
    "--plugin-version",
    "plugin_versions",
    metavar="DIST==VERSION",
    multiple=True,
    help="Pin a plugin distribution to a version, e.g. novapipe-foo==0.2.1"
)
def run(pipeline_file: str, vars: list, summary_path: str, metrics_port: int, metrics_path: str,
        plugin_versions: Any, ignore_failures: bool) -> None:
    """Run a pipeline YAML file."""
    with open(pipeline_file) as f:
        data = yaml.safe_load(f)

    # Parse and set plugin-version pins before loading
    pins: Dict[str, str] = {}
    for pv in plugin_versions:
        if "==" not in pv:
            click.echo(f"❌ Invalid --plugin-version format: {pv!r}. Expected DIST==VERSION", err=True)
            raise SystemExit(1)
        dist, ver = pv.split("==", 1)
        pins[dist] = ver
    set_plugin_pins(pins)
    load_plugins()

    # Derive a pipeline name from the file, e.g. 'pipeline.yaml' -> 'pipeline'
    pipeline_name = os.path.splitext(os.path.basename(pipeline_file))[0]
    runner = PipelineRunner(data, pipeline_name=pipeline_name)

    # If global ignore-failures is set, override each task_model.ignore_failure
    if ignore_failures:
        for tm in runner.tasks_by_name.values():
            # If user explicitly set ignore_failure in YAML to False, respect that
            if not hasattr(tm, "ignore_failure") or tm.ignore_failure is False:
                tm.ignore_failure = False

    # Parse CLI vars and seed runner.context
    for var_pair in vars:
        if "=" not in var_pair:
            click.echo(f"❌ Invalid --var format: {var_pair!r}. Use KEY=VAL.", err=True)
            raise SystemExit(1)
        key, val = var_pair.split("=", 1)
        runner.context[key] = val

    start = time.time()
    try:
        # Start metrics server if requested, on the configured path
        if metrics_port:
            class _MetricsHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == metrics_path:
                        self.send_response(200)
                        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                        self.end_headers()
                        self.wfile.write(generate_latest())
                    else:
                        self.send_response(404)

            httpd = HTTPServer(("0.0.0.0", metrics_port), _MetricsHandler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            click.echo(f"📊 Metrics available at http://localhost:{metrics_port}{metrics_path}")

        # Measure overall pipeline duration & status
        start = time.time()
        summary = runner.run()  # now returns PipelineRunSummary, with seeded context used in templates
        dur = time.time() - start

        # Record pipeline-level metrics
        PIPELINE_STATUS.labels(pipeline=pipeline_name, status="success").inc()
        PIPELINE_DURATION.labels(pipeline=pipeline_name).observe(dur)

        click.echo("✅ Pipeline completed (check logs for details).")

        # If we're serving metrics, keep the process alive until Ctrl+C
        if metrics_port:
            click.echo("🔒 Metrics server still running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\n👋 Shutting down metrics server and exiting.")

        if summary_path:
            # Write JSON summary to disk
            import json

            out = {"tasks": summary.to_list()}
            with open(summary_path, "w") as jf:
                json.dump(out, jf, indent=2)
            click.echo(f"📝 Summary written to {summary_path}")
    except Exception as e:
        # Record pipeline failure metric
        dur = time.time() - start
        PIPELINE_STATUS.labels(pipeline=pipeline_name, status="failed").inc()
        PIPELINE_DURATION.labels(pipeline=pipeline_name).observe(dur)

        click.echo(f"❌ Pipeline failed: {e}", err=True)
        raise SystemExit(1)


@cli.command("report")
@click.argument(
    "summary_json",
    type=click.Path(exists=True, dir_okay=False),
)
def report(summary_json):
    """
    Read a summary JSON (as written by --summary-json) and print a table:
        name    status  attempts    duration(s)     error
    """
    # Load the JSON
    with open(summary_json) as f:
        data = json.load(f)

    tasks: List[Dict[str, Any]] = data.get("tasks", [])
    if not tasks:
        click.echo("No tasks found in summary.", err=True)
        return

    # Prepare rows
    headers = ["Name", "Status", "Attempts", "Duration(s)", "Error"]
    rows = []
    for t in tasks:
        rows.append([
            t.get("name", ""),
            t.get("status", ""),
            str(t.get("attempts", "")),
            f"{t.get('duration_secs', 0):.3f}",
            t.get("error") or "",
        ])

    # Try using tabulate if available
    try:
        from tabulate import tabulate
        table = tabulate(rows, headers=headers, tablefmt="github")
        click.echo(table)
    except ImportError:
        # Fallback to simple padding
        # compute max widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        # header line
        hdr = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        click.echo(hdr)
        click.echo("-" * len(hdr))
        # rows
        for row in rows:
            line = "  ".join(row[i].ljust(widths[i]) for i in range(len(headers)))
            click.echo(line)


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

    # Render as Markdown if Rich is available, else plain text
    try:
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()
        console.print(Markdown(doc))
    except ImportError:
        click.echo(doc)

    # If this is a plugin task, show where it came from
    info = plugin_info.get(task_name)
    if info:
        click.echo()
        click.echo("Plugin Metadata:")
        click.echo(f" • Distribution: {info['distribution']} (v{info['version']})")
        click.echo(f" • Module:       {func.__module__}")


@cli.command("tutorial")
@click.argument("task_name")
def tutorial(task_name):
    """
    Emit a "Try-me" pipeline YAML snippet for TASK_NAME.
    """
    load_plugins()
    func = task_registry.get(task_name)
    if not func:
        click.echo(f"❌ Task {task_name!r} not found.", err=True)
        raise SystemExit(1)

    doc = _inspect.getdoc(func) or ""
    # 1) Try to extract an Example: block
    # We look for lines starting with "Example:" and take the indented block after it.
    example_match = re.search(
        r"Example:\s*\n((?:[ \t]+.*\n?)+)", doc, flags=re.IGNORECASE
    )
    if example_match:
        snippet = textwrap.dedent(example_match.group(1))
        click.echo("Here's a usage example from the docstring:\n")
        click.echo(snippet.rstrip())
        return

    # 2) Fallback: minimal skeleton
    click.echo(f"# Demo pipeline for `{task_name}`\n")
    click.echo("tasks:")
    click.echo(f"  - name: example_{task_name}")
    click.echo(f"    task: {task_name}")
    click.echo("    params:")
    click.echo("      # TODO: fill in parameters for this task")
    click.echo("\n# Run with:")
    click.echo(f"#   novapipe run pipeline.yaml")


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


@plugin.command("ci-template")
@click.argument(
    "output_path",
    type=click.Path(dir_okay=False, writable=True),
    default=".github/workflows/publish-plugin.yml",
)
def plugin_ci_template(output_path):
    """
    Scaffold a GitHub Actions workflow to build, test, and publish this plugin.
    """
    template = """\
name: Publish NovaPipe Plugin

on:
  push:
    tags:
      - 'v*'  # Trigger on any tag like v1.2.3

jobs:
  build-test-publish:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'  # or matrix 3.8–3.12

      - name: Install Poetry
        run: |
          pip install poetry

      - name: Configure PyPI token
        run: |
          poetry config pypi-token.pypi ${{{{ secrets.PYPI_API_TOKEN }}}}

      - name: Install dependencies
        run: |
          poetry install --no-dev

      - name: Run tests
        run: |
          poetry run pytest --cov=.

      - name: Build distribution
        run: |
          poetry build

      - name: Publish to PyPI
        run: |
          poetry publish --no-interaction --username __token__ --password ${{{{ secrets.PYPI_API_TOKEN }}}}

      - name: Create GitHub Release
        uses: ncipollo/release-action@v1
        with:
          tag: ${{{{ github.ref_name }}}}
"""
    # Ensure parent directories exist
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        f.write(template)
    click.echo(f"✅ CI workflow scaffolded to {output_path}")
    click.echo("👉 Next steps:")
    click.echo("   • Add PYPI_API_TOKEN as a secret in your repo settings")
    click.echo("   • Commit and push this file to `.github/workflows/`")
    click.echo("   • Tag a new release (`git tag v0.1.0 && git push --tags`) to trigger it")


@plugin.command("list")
@click.option(
    "--dist",
    "dists",
    metavar="DIST",
    multiple=True,
    help="Only show plugins from this distribution (can repeat).",
)
@click.option(
    "--task",
    "tasks_filter",
    metavar="TASK_SUBSTR",
    multiple=True,
    help="Only show entries whose task name contains this substring (can repeat).",
)
@click.option(
    "--source",
    "sources",
    metavar="MODULE_SUBSTR",
    multiple=True,
    help="Only show entries whose module path contains this substring (can repeat).",
)
def plugin_list(dists, tasks_filter, sources):
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

                # Apply filters immediately
                if dists and name not in dists:
                    continue
                if tasks_filter and not any(f in task_name for f in tasks_filter):
                    continue
                if sources and not any(s in module for s in sources):
                    continue

                key = f"{name} (v{version})"
                plugins.setdefault(key, []).append((task_name, module))

    if not plugins:
        click.echo("No matching NovaPipe plugins installed.")
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


@cli.group("repo")
def repo():
    """
    Manage CI/CD workflows for the NovaPipe repository itself.
    """
    pass


@repo.command("ci-template")
@click.argument(
    "output_path",
    type=click.Path(dir_okay=False, writable=True),
    default=".github/workflows/release.yml",
)
def repo_ci_template(output_path):
    """
    Scaffold a GitHub Actions workflow for canary (TestPyPI) and stable (PyPI) releases.
    """
    template = """\
name: Release NovaPipe

on:
  push:
    branches:
      - main
  push:
    tags:
      - 'v*'

jobs:
  canary:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Poetry
        run: pip install poetry

      - name: Configure TestPyPI token
        run: poetry config repositories.testpypi https://test.pypi.org/legacy/ && \\
             poetry config pypi-token.testpypi ${{{{ secrets.TESTPYPI_API_TOKEN }}}}

      - name: Install dependencies
        run: poetry install --no-dev

      - name: Bump to canary version
        # e.g. from 1.2.3 to 1.2.4-dev$(date +%Y%m%d%H%M)
        run: |
          base=$(poetry version -s)
          stamp=$(date +%Y%m%d%H%M)
          poetry version "${{ base }}-dev${{ stamp }}"

      - name: Build distribution
        run: poetry build

      - name: Publish to TestPyPI
        run: |
          poetry publish --repository testpypi --username __token__ \\
            --password ${{{{ secrets.TESTPYPI_API_TOKEN }}}}

  stable:
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    needs: canary
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Poetry
        run: pip install poetry

      - name: Configure PyPI token
        run: poetry config pypi-token.pypi ${{{{ secrets.PYPI_API_TOKEN }}}}

      - name: Install dependencies
        run: poetry install --no-dev

      - name: Build distribution
        run: poetry build

      - name: Publish to PyPI
        run: |
          poetry publish --no-interaction --username __token__ \\
            --password ${{{{ secrets.PYPI_API_TOKEN }}}}
"""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template)
    click.echo(f"✅ Repository CI workflow scaffolded to {output_path}")
    click.echo("👉 Next steps:")
    click.echo("   • Add secrets TESTPYPI_API_TOKEN & PYPI_API_TOKEN in Settings → Secrets")
    click.echo("   • Commit and push this file to .github/workflows/")
    click.echo("   • Pushing to main creates a TestPyPI canary; tagging vX.Y.Z on GitHub publishes to PyPI")


@cli.command("playground")
@click.option(
    "--var", "-D",
    "vars",
    metavar="KEY=VAL",
    multiple=True,
    help="Seed the playground context with KEY=VAL (can repeat).",
)
@click.argument("template", required=False)
def playground(vars, template):
    """
    Interactive Jinja2 playground

    If TEMPLATE is given, renders it once and exits.
    Otherwise enters a REPL: type templates, ENTER to render, or 'exit' or quit.
    """
    # Build the Jinja2 env like NovaPipe uses
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    env.globals.update({'int': int, 'float': float, 'str': str, 'bool': bool, 'len': len})

    # Seed context
    context = {}
    for var in vars:
        if "=" not in var:
            click.echo(f"❌ Invalid var: {var!r}. Use KEY=VAL.", err=True)
            return
        k, v = var.split("=", 1)
        # Try to parse JSON for numbers/bools/lists, else keep string
        try:
            context[k] = json.loads(v)
        except Exception:
            context[k] = v

    click.echo(f"🔧 Playground context: {context!r}")

    def render_and_print(tmpl_str: str):
        try:
            tmpl = env.from_string(tmpl_str)
            out = tmpl.render(**context)
            click.echo(out)
        except Exception as e:
            click.echo(f"⚠️  Error: {e}", err=True)

    if template:
        # One-off render
        render_and_print(template)
        return

    # REPL mode
    click.echo("📝 Enter templates; type 'exit' or Ctrl-D to quit.")
    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            click.echo("\n👋 Exiting playground.")
            break
        if not line or line.strip().lower() in ("exit", "quit"):
            click.echo("👋 Goodbye.")
            break
        render_and_print(line)


if __name__ == '__main__':
    cli(prog_name="novapipe")
