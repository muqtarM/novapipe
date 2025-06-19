# Plugin Development

Extend NovaPipe by writing your own plugin packages. Plugins can define new tasks, which are discovered via Python entry points.

---

## 1. Scaffold a New Plugin

Run:

```bash
novapipe plugin scaffold myplugin
```

This creates a directory `myplugin/` with:

```
myplugin/
├── pyproject.toml
└── src/
    └── myplugin/
        └── tasks.py
```

- **`pyproject.toml`**: with Poetry setup for packaging.  
- **`src/myplugin/tasks.py`**: where you implement your `@task` functions.

---

## 2. Define Tasks

In `tasks.py`, import NovaPipe’s `@task` decorator:

```python
from typing import Dict, Any
from novapipe.tasks import task

@task
def my_task(params: Dict[str, Any]) -> Any:
    '''
    Docstring explaining `my_task`...

    Example:
        tasks:
          - name: example_my_task
            task: my_task
            params:
              foo: 1
    '''
    # Your implementation here
    result = params.get("foo", 0) * 2
    return result
```

- **Function signature**: `fn(params: Dict[str, Any]) -> Any`.  
- **Docstring**: include an `Example:` section to power `novapipe tutorial`.  

---

## 3. Entry-Point Discovery

Poetry’s `pyproject.toml` should include:

```toml
[tool.poetry.plugins."novapipe.plugins"]
"my_task" = "myplugin.tasks:my_task"
```

NovaPipe will discover tasks under the `novapipe.plugins` group automatically.

---

## 4. Version-Gating & Conflict Resolution

If multiple plugins define the same task name, you can pin versions:

```bash
novapipe run pipeline.yaml   --plugin-version myplugin==0.1.0
```

This ensures NovaPipe uses exactly your specified plugin distribution.

---

## 5. Plugin CI Template

Scaffold a GitHub Actions workflow for your plugin:

```bash
novapipe plugin ci-template
```

This writes `.github/workflows/publish-plugin.yml`, which:

- Checks out code  
- Installs Poetry  
- Runs tests  
- Builds & publishes to PyPI  

---

## 6. Publishing Your Plugin

1. Commit and tag a release, e.g.:

   ```bash
   git tag v0.1.0
   git push --tags
   ```

2. The CI template will publish to PyPI automatically (requires `PYPI_API_TOKEN` secret).

---

## 7. Discover Installed Plugins

List all plugins you have installed:

```bash
novapipe plugin list
```

Use filters:

- `--dist DISTRO_NAME`  
- `--task SUBSTR`  
- `--source MODULE_PATH`  

---

Congratulations — you’re now ready to develop, test, and publish NovaPipe plugins!
