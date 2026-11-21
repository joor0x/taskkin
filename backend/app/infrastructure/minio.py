from typing import Any

import boto3
from botocore.config import Config

from app.config import settings


def get_s3_client() -> Any:
    """Get a boto3 S3 client configured for MinIO."""
    # Build endpoint URL based on secure flag
    protocol = "https" if settings.MINIO_SECURE else "http"
    endpoint_url = f"{protocol}://{settings.MINIO_ENDPOINT}"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",  # Dummy region name for MinIO compatibility
    )


def ensure_bucket_exists() -> None:
    """Ensure the evidence bucket exists in MinIO."""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.MINIO_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=settings.MINIO_BUCKET)
