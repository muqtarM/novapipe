# Quickstart

This guide gets you up and running with NovaPipe in under 5 minutes.

## 1. Install NovaPipe

Install the latest release from PyPI:

```bash
pip install novapipe
```

## 2. Define Your Pipeline

Create a file named `pipeline.yaml` with the following content:

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

- **`name`**: a unique identifier for each step.  
- **`task`**: the function to run (built-in or plugin).  
- **`params`**: key/value arguments, can use Jinja2 templating.  
- **`depends_on`**: optional list of task names to enforce ordering.

## 3. Run the Pipeline

Execute the pipeline with:

```bash
novapipe run pipeline.yaml   --var environment=prod   --summary-json summary.json   --metrics-port 8000   --metrics-path /mymetrics
```

- `--var KEY=VAL` injects variables into Jinja2 context.  
- `--summary-json` writes a JSON report of the run.  
- `--metrics-port` and `--metrics-path` serve Prometheus metrics.

## 4. View the Report

After completion, view a human-friendly table:

```bash
novapipe report summary.json
```

Example output:

| Name     | Status  | Attempts | Duration(s) | Error |
|----------|---------|----------|-------------|-------|
| extract  | success | 1        | 0.123       |       |
| transform| success | 1        | 0.045       |       |
| load     | success | 1        | 0.010       |       |

## 5. Explore Further

- **Inspect tasks**: `novapipe inspect`  
- **Describe a task**: `novapipe describe write_text_file`  
- **Get a tutorial snippet**: `novapipe tutorial write_text_file`  
- **Visualize the DAG**: `novapipe dag pipeline.yaml --dot`  
- **Interactive playground**:  
  ```bash
  novapipe playground --var a=10 --var b=20 "{{ a * b }}"
  ```

Next, check out the **CLI Reference** to learn all available commands and options.
