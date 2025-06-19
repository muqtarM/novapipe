# Rate Limiting

NovaPipe supports **per-endpoint rate limiting** via a simple token-bucket algorithm.  
Use `rate_limit` (calls per second) and `rate_limit_key` (group identifier) in your task definitions.

---

## Configuration

Add the following fields to your task in `pipeline.yaml`:

- **`rate_limit`**: Maximum allowed calls per second (float).
- **`rate_limit_key`** _(optional)_: Identifier for grouping tasks under the same rate limit (defaults to the task name).

```yaml
tasks:
  - name: fetch_page1
    task: call_api
    rate_limit: 2            # up to 2 calls per second
    rate_limit_key: "api"    # shared bucket for API calls
    params:
      url: "https://example.com/page1"

  - name: fetch_page2
    task: call_api
    rate_limit: 2
    rate_limit_key: "api"
    params:
      url: "https://example.com/page2"

  - name: aggregate
    task: aggregate_results
    depends_on:
      - fetch_page1
      - fetch_page2
```

- Here, `fetch_page1` and `fetch_page2` share the same bucket `"api"`, so together they will not exceed **2 calls/sec**.

---

## How It Works

Under the hood, NovaPipe:

1. Initializes a single `RateLimiter(rate, per=1.0)` per unique `rate_limit_key`.
2. Before each task execution, calls `await limiter.acquire()`:
   - Maintains a timestamp deque of recent calls.
   - If the number of calls in the last second `< rate`, proceeds immediately.
   - Otherwise, sleeps until the next slot is available.
3. Ensures sliding-window compliance across concurrent tasks in the same “layer”.

---

## Running & Testing

Run your pipeline as usual:

```bash
novapipe run pipeline.yaml
```

No additional flags are required.

### Example

```bash
novapipe run rate_limit_pipeline.yaml
```

Tasks will automatically throttle to the configured limits.

### Automated Test

NovaPipe includes a unit test `tests/test_runner_rate_limit.py`:

```python
def test_rate_limit(tmp_path):
    # two tasks sharing rate_limit_key "group" at 1 call/sec
    ...
    assert abs(t2 - t1) >= 0.9
```

This verifies that back-to-back tasks honor the specified rate.

---

For more advanced patterns, see **Resource & Env** and **Observability** guides.  
