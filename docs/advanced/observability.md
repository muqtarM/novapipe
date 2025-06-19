# Observability

NovaPipe offers comprehensive observability features for monitoring and troubleshooting your pipelines.

---

## Structured Logging

NovaPipe logs with contextual, structured messages:

- **Timestamps** and **log levels** (INFO, DEBUG, ERROR).  
- Task-specific information: task name, attempt count, status, and duration.

Example log:

```
[INFO] novapipe: Task 'extract' succeeded on attempt 1/1 in 0.123s
[ERROR] novapipe: Task 'transform' failed on attempt 3/3: TimeoutError('...')
```

Use `--verbose` to enable DEBUG-level logs:

```bash
novapipe run pipeline.yaml --verbose
```

---

## JSON Summary

After each run, use `--summary-json` to write a detailed summary:

```bash
novapipe run pipeline.yaml --summary-json summary.json
```

The output JSON includes an array of task records:

```json
{
  "tasks": [
    {
      "name": "extract",
      "status": "success",
      "attempts": 1,
      "duration_secs": 0.123,
      "error": null
    },
    ...
  ]
}
```

Use `novapipe report summary.json` to see a human-friendly table.

---

## Human-Friendly Report

Convert the JSON summary into a markdown-style table:

```bash
novapipe report summary.json
```

Example output:

| Name      | Status         | Attempts | Duration(s) | Error                           |
|-----------|----------------|----------|-------------|---------------------------------|
| extract   | success        | 1        | 0.123       |                                 |
| transform | failed_ignored | 3        | 2.456       | RuntimeError('Simulated fail')  |
| load      | success        | 1        | 0.010       |                                 |

---

## Prometheus Metrics

Enable Prometheus endpoint with:

```bash
novapipe run pipeline.yaml --metrics-port 8000 --metrics-path /metrics
```

Metrics served:

- **Per-task counters**:
  - `novapipe_task_status_total{pipeline,task,status}`
- **Per-task histograms**:
  - `novapipe_task_duration_seconds_bucket{pipeline,task,status,le}`
- **Pipeline-level counters**:
  - `novapipe_pipeline_status_total{pipeline,status}`
- **Pipeline-level histograms**:
  - `novapipe_pipeline_duration_seconds_bucket{pipeline,le}`

### Custom Path

Use `--metrics-path` to customize endpoint:

```bash
--metrics-path /mymetrics
```

Then metrics are at `http://localhost:8000/mymetrics`.

### Grafana Integration

Example scrape config:

```yaml
scrape_configs:
  - job_name: novapipe
    metrics_path: /metrics
    static_configs:
      - targets: ['localhost:8000']
```

---

## Summary

NovaPipe’s observability stack enables:

- **Real-time metrics** for dashboards.  
- **Structured logs** for troubleshooting.  
- **JSON & human reports** for CI/CD and manual review.

Use these tools to gain full visibility into your pipeline executions and performance.
