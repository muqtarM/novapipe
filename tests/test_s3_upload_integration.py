import os
import yaml
import tempfile
import boto3

from click.testing import CliRunner
from javpy.runner import PipelineRunner  # adjust import if needed
from novapipe.cli import cli  # for CLI invocation

# Register the upload task, if not already auto-discovered
# from novapipe.tasks import task  # assume upload_file_s3 is in tasks


def test_upload_file_s3_integration(s3_bucket, tmp_path):
    client, bucket = s3_bucket

    # Create a small temp file
    local_file = tmp_path / "hello.txt"
    local_file.write_text("Hello, Moto!")

    # Pipeline YAML that uses our upload_file_s3 task
    pipeline = {
        "tasks": [
            {
                "name": "upload",
                "task": "upload_file_s3",
                "params": {
                    "bucket": bucket,
                    "key": "folder/hello.txt",
                    "path": str(local_file),
                },
            }
        ]
    }

    runner = PipelineRunner(pipeline, pipeline_name="s3test")
    summary = runner.run()
    # Ensure task succeeded
    stats = {t["name"]: t for t in summary.to_list()}
    assert stats["upload"]["status"] == "success"

    # Verify object exists in fake S3
    resp = client.get_object(Bucket=bucket, Key="folder/hello.txt")
    body = resp["Body"].read().decode()
    assert body == "Hello, Moto!"
