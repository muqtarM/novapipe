# NovaPipe

[![PyPI version](https://img.shields.io/pypi/v/novapipe.svg)](https://pypi.org/project/novapipe)  
[![Build Status](https://github.com/muqtarM/novapipe/actions/workflows/release.yml/badge.svg)](https://github.com/muqtarM/novapipe/actions)  
[![Coverage Status](https://img.shields.io/codecov/c/github/your-org/novapipe.svg)](https://codecov.io/gh/muqtarM/novapipe)  
[![Documentation Status](https://readthedocs.org/projects/novapipe/badge/?version=latest)](https://novapipe.readthedocs.io/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

> **NovaPipe** — lightweight, plugin-driven ETL & orchestration for Python.

## 🎯 Quickstart

Install from PyPI:

```bash
pip install novapipe
```

Create `pipeline.yaml`:

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

Run it:

```bash
novapipe run pipeline.yaml \
  --var environment=prod \
  --summary-json summary.json \
  --metrics-port 8000
```

View a human-friendly report:

```bash
novapipe report summary.json
```

---

## 🚀 Features

|Category	| Features |
|-----------|----------|
|Core CLI	| `init`, `run`, `inspect`, `describe`, `tutorial`, `dag`, `report`, `playground`|
|Plugin Mgmt.	|Scaffold, list (with filters), CI-template, version-gating|
|Pipeline Modeling	|`run_if`/`run_unless`, branches, skip-downstream, retries, timeouts, ignore-failures|
|Execution Engine	|Async/sync, layered parallelism, resource tagging, rate-limit|
|Templating & Context	|Jinja2 with built-ins, multi-output unpacking, CLI vars, interactive REPL|
|Resource & Env	|CPU/memory caps, rate limits, env injection|
|Observability	|Structured logging, JSON summary, human report, Prometheus metrics|
|Testing & CI/CD	|Unit & integration tests, plugin + repo CI templates|

---

## 📖 Documentation

Full docs and examples are hosted on ReadTheDocs:

> https://novapipe.readthedocs.io/

---

## 💡 Getting Help

- Ask questions on [Discussions](https://github.com/muqtarM/novapipe/discussions)

- Report bugs via [Issues](https://github.com/muqtarM/novapipe/issues)

---

## 🤝 Contributing

1. Fork & clone
2. `poetry install` (or `pip install -e .[dev]`)
3. Create a feature branch, commit, and open a PR
4. Ensure tests pass: `pytest`

See CONTRIBUTING.md & CODE_OF_CONDUCT.md for details.

---

## 📜 License

MIT © Muqtar Shaikh

1. **Replace** badge URLs with your actual GitHub org/repo and PyPI project names.  
2. **Link** the Quickstart to real example pipelines in your `examples/` folder.  
3. **Populate** the “Features” table with any additional items as you add them.  


