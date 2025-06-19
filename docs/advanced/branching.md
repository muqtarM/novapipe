# Branching

NovaPipe supports **sub-pipeline branching**, allowing you to group tasks into named branches and toggle them on/off via a single condition.

---

## Defining Branches

At the top level of your `pipeline.yaml`, add a `branches` section:

```yaml
branches:
  dev:  "{{ environment == 'dev' }}"
  prod: "{{ environment == 'prod' }}"
```

- **Key**: branch name (`dev`, `prod`, etc.)  
- **Value**: a Jinja2 expression that evaluates to **true** or **false** given the current context.

## Assigning Tasks to Branches

In each task, use the `branch` field:

```yaml
tasks:
  - name: extract_dev
    task: extract_data
    branch: dev
    params:
      source: "dev_db"

  - name: extract_prod
    task: extract_data
    branch: prod
    params:
      source: "prod_db"

  - name: transform
    task: transform_data
    params:
      input: "{{ extract_dev or extract_prod }}"
    depends_on:
      - extract_dev
      - extract_prod

  - name: load
    task: load_data
    params:
      path: "{{ transform }}"
    depends_on:
      - transform
```

- Only tasks whose branch condition evaluates **true** will run; others are **skipped**.  
- Downstream tasks with mixed dependencies still run once all predecessors have completed or skipped.

## Running with a Branch

Provide a context variable (e.g. via `--var`) that controls the branch:

```bash
novapipe run pipeline.yaml --var environment=dev
```

- Runs only tasks in the `dev` branch plus any unbranched tasks.  
- The `extract_prod` task would be skipped.

## Example

```bash
# Pipeline file: pipeline.yaml
novapipe run pipeline.yaml --var environment=prod
```

Output will show:
```
[SKIPPED] extract_dev  (branch 'dev' = false)
[SUCCESS] extract_prod
[SUCCESS] transform
[SUCCESS] load
```

---

## Testing Branching

NovaPipe includes unit tests for branching:

```python
from novapipe.runner import PipelineRunner
import yaml

runner = PipelineRunner(..., pipeline_name="test")
runner.context["environment"] = "prod"
summary = runner.run()
```

See `tests/test_branching.py` for details.
