from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str
    mongo_landing_collection: str
    mongo_processed_collection: str

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_landing_bucket: str
    minio_processed_bucket: str


def load_settings() -> Settings:
    return Settings(
        mongo_uri=os.environ["MONGO_URI"],
        mongo_db=os.environ["MONGO_DB"],
        mongo_landing_collection=os.environ["MONGO_LANDING_COLLECTION"],
        mongo_processed_collection=os.environ["MONGO_PROCESSED_COLLECTION"],
        minio_endpoint=os.environ["MINIO_ENDPOINT"],
        minio_access_key=os.environ["MINIO_ROOT_USER"],
        minio_secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        minio_landing_bucket=os.environ["MINIO_LANDING_BUCKET"],
        minio_processed_bucket=os.environ["MINIO_PROCESSED_BUCKET"],
    )


settings = load_settings()
