import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


# Simple tasks
@task
def return_value(params):
    return params.get("value")


@task
def echo(params):
    print(params.get("msg", ""))
    return params.get("msg", "")


@pytest.mark.parametrize("env,run_dev,run_prod", [
    ("dev", True, False),
    ("prod", False, True),
    ("other", False, False),
])
def test_branching(env, run_dev, run_prod, caplog):
    caplog.set_level(logging.INFO, logger="novapipe")

    pipeline = f"""
branches:
  dev:  "{{{{ environment == 'dev' }}}}"
  prod: "{{{{ environment == 'prod' }}}}"

tasks:
  - name: task_dev
    task: echo
    branch: dev
    params:
      msg: "DEV"

  - name: task_prod
    task: echo
    branch: prod
    params:
      msg: "PROD"

  - name: always
    task: echo
    params:
      msg: "ALWAYS"
    depends_on:
      - task_dev
      - task_prod
"""
    data = yaml.safe_load(pipeline)
    runner = PipelineRunner(data, pipeline_name="branch_test")
    # Seed env var
    runner.context["environment"] = env

    summary = runner.run()
    stats = {t["name"]: t for t in summary.to_list()}

    assert stats["always"]["status"] == "success"

    if run_dev:
        assert stats["task_dev"]["status"] == "success"
    else:
        assert stats["task_dev"]["status"] == "skipped"

    if run_prod:
        assert stats["task_prod"]["status"] == "success"
    else:
        assert stats["task_prod"]["status"] == "skipped"
