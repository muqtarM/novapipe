# NovaPipe

**NovaPipe** is a lightweight, plugin-driven ETL and orchestration toolkit for Python.  
Define your data pipelines in plain YAML, extend with plugins, and run them via a simple CLI—all with rich templating, reliability controls, and observability built-in.

---

## 🚀 Quickstart

1. **Install**  
   ```bash
   pip install novapipe
   ```

2. **Write a pipeline** (`pipeline.yaml`):  
   ```yaml
   tasks:
     - name: extract
       task: extract_data
       params:
         source: "s3://my-bucket/input.csv"

     - name: transform
       task: transform_data
       params:
         input_path: "{{ extract }}"
       depends_on:
         - extract

     - name: load
       task: load_data
       params:
         path: "{{ transform }}"
       depends_on:
         - transform
   ```

3. **Run**  
   ```bash
   novapipe run pipeline.yaml      --var environment=prod      --summary-json summary.json      --metrics-port 8000      --metrics-path /mymetrics
   ```

4. **Inspect**  
   - List tasks: `novapipe inspect`  
   - Show task docs: `novapipe describe write_text_file`  
   - Get a tutorial snippet: `novapipe tutorial write_text_file`  
   - Visualize DAG: `novapipe dag pipeline.yaml --dot`  

5. **Report**  
   ```bash
   novapipe report summary.json
   ```

6. **Playground**  
   ```bash
   novapipe playground --var a=5 --var b=7 "{{ a + b }}"
   ```

---

## ✨ Key Features

### 1. Core CLI & UX
- **Commands**: `init`, `run`, `inspect`, `describe`, `tutorial`, `dag`, `report`, `playground`  
- **Global flags**: `--var` CLI vars, `--summary-json`, `--metrics-port`, `--metrics-path`, `--ignore-failures`  
- **Subcommands**:  
  - **Plugin**: `scaffold`, `list` (with `--dist`, `--task`, `--source`), `ci-template`  
  - **Repo**: `repo ci-template` for canary vs. stable releases  

### 2. Plugin Architecture
- **Decorator-based** `@task` registry  
- **Entry-point discovery** via `novapipe.plugins`  
- **Conflict resolution** / **version-gating** with `--plugin-version`  
- **Plugin CI** scaffold for publishing to PyPI  

### 3. Pipeline Schema & Validation
- **Pydantic models** for `TaskModel` & `Pipeline`  
- Fields: `name`, `task`, `params`, `depends_on`  
- **Validation**: non-empty, unique task names, branch existence  

### 4. Reliability & Control
- **Retries**: `retries`, `retry_delay`  
- **Timeouts**: `timeout`  
- **Ignore failures**: per-task & global `--ignore-failures`  
- **Conditional execution**: `run_if`, `run_unless`  
- **Sub-pipeline branching**: top-level `branches`, per-task `branch`  
- **Skip downstream on failure**: `skip_downstream_on_failure`  

### 5. Execution Engine
- **Topological sort** → layered concurrency  
- **Async & sync support** via `asyncio` + thread-pool  
- **Multi-output unpacking**: dict → multiple context variables  
- **Resource tags** & **max_concurrency** for I/O throttling  
- **Rate limiting**: `rate_limit`, `rate_limit_key` (sliding-window token bucket)  

### 6. Templating & Context
- **Jinja2** parameter rendering with `StrictUndefined`  
- Exposed built-ins: `int`, `float`, `str`, `bool`, `len`  
- **CLI var injection** (`--var KEY=VAL`)  
- **Interactive REPL** (`playground`) for experimenting  

### 7. Resource & Environment Management
- **CPU & memory caps** with `cpu_time`, `memory` (UNIX `resource`-based)  
- **Per-task env injection** via `env` field (templated → `os.environ`)  

### 8. Observability & Reporting
- **Structured logging** (INFO/DEBUG)  
- **JSON summary** of every run (`--summary-json`)  
- **Human-friendly table** (`report`)  
- **Prometheus metrics**:  
  - Per-task & pipeline histograms & counters (`--metrics-port`, `--metrics-path`)  
  - Labels: `pipeline`, `task`, `status`  

### 9. Documentation & Developer Experience
- **Auto-generated tutorial snippets** (`tutorial`)  
- **Markdown-rendered** docstrings in `describe` (via Rich)  
- **ReadTheDocs** & **MkDocs**-based docs with `mkdocstrings`  

### 10. Testing & CI/CD
- **Unit tests** for all features  
- **Integration tests** (e.g. S3 via Moto)  
- **Codecov** coverage reporting  
- **CI templates** for both NovaPipe repo and plugins  

---

## 🛣️ What’s Next

- Browse the **Quickstart** → `docs/quickstart.md`  
- Explore **CLI Reference** → `docs/cli.md`  
- Learn **Plugin Development** → `docs/plugin_development.md`  
- Dive into **Advanced Usage** sections for branching, rate limiting, resource/env, observability  
- Contribute: see **Contributing** → `docs/contributing.md`  

---

## 📖 Full API Reference

Auto-generated from code: see **API Reference** → `docs/reference/novapipe.md`

---

> For questions and discussion, enable **Discussions** on GitHub:  
> https://github.com/your-org/novapipe/discussions  
