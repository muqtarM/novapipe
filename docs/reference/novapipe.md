# API Reference

This page provides a detailed API reference for NovaPipe modules, classes, and functions.  
Powered by **mkdocstrings**, each section below will automatically list available attributes and docstrings.

---

## Core Modules

### novapipe.tasks

Discover and register task functions for pipelines.

::: novapipe.tasks

---

### novapipe.cli

The command-line interface definitions, including commands, options, and subcommands.

::: novapipe.cli

---

### novapipe.models

Pydantic models defining the pipeline schema: `TaskModel` and `Pipeline`.

::: novapipe.models

---

### novapipe.runner

The execution engine for pipelines: `PipelineRunner`, `RateLimiter`, and helper functions.

::: novapipe.runner

---

### PipelineRunSummary (in novapipe.runner)

::: novapipe.runner.PipelineRunSummary

---

## Helper Utilities

- **limit_and_call**: Apply resource limits before executing tasks.  
- **set_plugin_pins**: Pin plugin versions for conflict resolution.

Refer to the sections above for these utilities where applicable.

---

*Automatically generated.sections will be populated by `mkdocstrings` when building the docs.*
