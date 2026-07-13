from __future__ import annotations

from common.blob_storage import ensure_bucket, upload_bytes
from common.config import settings
from common.content_types import CONTENT_TYPES
from common.hashing import normalize_html_for_hash, sha256_of_bytes
from common.mongo import get_landing_collection

METADATA_FIELDS = ("title", "description", "date", "doc_url", "detail_url", "partition_date")


class IdempotentStoragePipeline:
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self):
        self.collection = get_landing_collection()
        self.collection.create_index("identifier", unique=True)
        ensure_bucket(settings.minio_landing_bucket)

    def process_item(self, item):
        spider = self.crawler.spider
        raw_content = item.pop("raw_content")
        hashable_content = normalize_html_for_hash(raw_content) if item["file_type"] == "html" else raw_content
        file_hash = sha256_of_bytes(hashable_content)

        stats = spider.stats_by_partition[(item["body"], item["partition_date"])]
        existing = self.collection.find_one({"identifier": item["identifier"]})

        safe_identifier = item["identifier"].replace("/", "-")
        key = f"{item['body']}/{safe_identifier}.{item['file_type']}"
        item["file_hash"] = file_hash
        item["file_path"] = f"s3://{settings.minio_landing_bucket}/{key}"

        content_unchanged = existing is not None and existing.get("file_hash") == file_hash
        if not content_unchanged:
            content_type = CONTENT_TYPES.get(item["file_type"], "application/octet-stream")
            upload_bytes(settings.minio_landing_bucket, key, raw_content, content_type=content_type)

        self.collection.update_one({"identifier": item["identifier"]}, {"$set": dict(item)}, upsert=True)

        log_fields = {"identifier": item["identifier"], "body": item["body"], "partition_date": item["partition_date"]}

        if content_unchanged:
            stats["skipped_unchanged"] += 1
            metadata_changed = any(existing.get(f) != item.get(f) for f in METADATA_FIELDS)
            spider.json_log.info("record_metadata_refreshed" if metadata_changed else "record_unchanged_skipped", extra=log_fields)
        else:
            stats["scraped"] += 1
            spider.json_log.info("record_updated" if existing else "record_inserted", extra={**log_fields, "file_type": item["file_type"]})

        return item
