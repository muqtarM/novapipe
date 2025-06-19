# Resource & Environment Management

NovaPipe provides fine-grained control over system resources and environment variables on a per-task basis.

---

## CPU & Memory Caps

Use `cpu_time` and `memory` to restrict resource usage (UNIX only):

- **`cpu_time`**: Maximum CPU-seconds allowed for the task (integer).
- **`memory`**: Maximum address-space (virtual memory) in bytes (integer).

```yaml
tasks:
  - name: crunch
    task: heavy_compute
    cpu_time: 10            # limit to 10 CPU-seconds
    memory: 536870912       # limit to 512 MiB of RAM
    params:
      n: 10000000
```

Under the hood, NovaPipe uses `resource.setrlimit` to enforce:

- `RLIMIT_CPU` for CPU time.
- `RLIMIT_AS` for address-space size.

If limits are exceeded, the task is terminated and treated as a failure (unless `ignore_failure` is set).

---

## Resource Tags & Concurrency

Throttle I/O-heavy tasks with `resource_tag` and `max_concurrency`:

- **`resource_tag`**: Logical name grouping tasks (e.g., `"http"`, `"db"`).
- **`max_concurrency`**: Maximum parallel executions for tasks sharing the same tag.

```yaml
tasks:
  - name: download1
    task: download_file
    resource_tag: http
    max_concurrency: 2
    params:
      url: "https://example.com/1"

  - name: download2
    task: download_file
    resource_tag: http
    max_concurrency: 2
    params:
      url: "https://example.com/2"
```

NovaPipe builds an `asyncio.Semaphore` per `resource_tag` to enforce these limits.

---

## Environment Variable Injection

Inject custom environment variables into the task execution context:

- **`env`**: key/value map; values are Jinja2 templates rendered against the pipeline context.

```yaml
tasks:
  - name: set_creds
    task: return_value
    params:
      value: "AKIA..."

  - name: upload
    task: upload_file_s3
    depends_on:
      - set_creds
    env:
      AWS_ACCESS_KEY_ID: "{{ set_creds }}"
      AWS_SECRET_ACCESS_KEY: "{{ secret_key }}"
    params:
      bucket: "my-bucket"
      key: "data/out.txt"
```

NovaPipe temporarily updates `os.environ` for the task, then restores it after completion.

---

## Combined Example

```yaml
tasks:
  - name: fetch
    task: fetch_data
    rate_limit: 5
    resource_tag: api
    max_concurrency: 3

  - name: process
    task: process_data
    cpu_time: 5
    memory: 104857600   # 100 MiB

  - name: publish
    task: publish_results
    env:
      API_TOKEN: "{{ secret }}"
    depends_on:
      - fetch
      - process
```

---

## Testing & Integration

- **CPU/Memory Limits**: `tests/test_runner_cpu_memory_limits.py`
- **Concurrency**: `tests/test_runner_resource_concurrency.py`
- **Env Injection**: `tests/test_runner_env_injection.py`

Check the repository’s `tests/` folder for examples.