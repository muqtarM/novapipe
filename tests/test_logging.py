# tests/test_logging.py

import yaml
import pytest
import logging

from novapipe.runner import PipelineRunner
from novapipe.tasks import task


@task
def quick(params):
    pass


def test_logging_output(caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="novapipe")
    pipeline_str = """
    tasks:
      - name: t
        task: quick
    """
    data = yaml.safe_load(pipeline_str)
    runner = PipelineRunner(data)
    runner.run()

    # Ensure we see "Pipeline completed successfully" in logs
    assert any("Pipeline completed successfully" in rec.message for rec in caplog.records)
