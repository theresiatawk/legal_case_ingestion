from __future__ import annotations

from pymongo import MongoClient
from pymongo.collection import Collection

from common.config import settings

_client: MongoClient | None = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri)
    return _client


def get_landing_collection() -> Collection:
    return get_client()[settings.mongo_db][settings.mongo_landing_collection]


def get_processed_collection() -> Collection:
    return get_client()[settings.mongo_db][settings.mongo_processed_collection]
