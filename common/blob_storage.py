from __future__ import annotations

import boto3
from botocore.client import BaseClient, Config
from botocore.exceptions import ClientError

from common.config import settings

_client: BaseClient | None = None


def get_client() -> BaseClient:
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
        )
    return _client


def ensure_bucket(bucket: str) -> None:
    client = get_client()
    existing = {b["Name"] for b in client.list_buckets()["Buckets"]}
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    get_client().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def download_bytes(bucket: str, key: str) -> bytes:
    return get_client().get_object(Bucket=bucket, Key=key)["Body"].read()


def object_exists(bucket: str, key: str) -> bool:
    try:
        get_client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise
