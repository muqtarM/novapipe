import os
import pytest
import boto3
from moto import mock_s3


@pytest.fixture(autouse=True)
def aws_credentials_env():
    """
    Ensure any boto3 client uses fake “testing” credentials.
    """
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
    os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
    yield
    # cleanup if needed


@pytest.fixture
def s3_bucket():
    """
    Start a moto S3 mock, create a bucket, and yield the client.
    """
    with mock_s3():
        conn = boto3.client("s3", region_name="us-east-1")
        bucket = "my-test-bucket"
        conn.create_bucket(Bucket=bucket)
        yield conn, bucket
