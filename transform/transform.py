from __future__ import annotations

import argparse
import html
from datetime import datetime

from bs4 import BeautifulSoup

from common.blob_storage import download_bytes, ensure_bucket, parse_s3_uri, upload_bytes
from common.config import settings
from common.content_types import CONTENT_TYPES
from common.hashing import sha256_of_bytes
from common.logging_utils import get_logger
from common.mongo import get_landing_collection, get_processed_collection

log = get_logger("transform")


def extract_relevant_content(raw_html: bytes, title: str) -> bytes:
    soup = BeautifulSoup(raw_html, "html.parser")
    content = soup.select_one("div.content")
    if content is None:
        content = soup.body or soup

    for tag in content.select("script, style"):
        tag.decompose()

    safe_title = html.escape(title)
    page = f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{safe_title}</title></head><body>{content}</body></html>'
    return page.encode("utf-8")


def transform_record(record: dict, processed_collection) -> tuple[dict, bool]:
    bucket, key = parse_s3_uri(record["file_path"])
    raw_content = download_bytes(bucket, key)

    if record["file_type"] == "html":
        content = extract_relevant_content(raw_content, record["identifier"])
    else:
        content = raw_content

    file_hash = sha256_of_bytes(content)
    safe_identifier = record["identifier"].replace("/", "-")
    new_key = f"{safe_identifier}.{record['file_type']}"

    existing = processed_collection.find_one({"identifier": record["identifier"]})
    content_unchanged = existing is not None and existing.get("file_hash") == file_hash

    if not content_unchanged:
        content_type = CONTENT_TYPES.get(record["file_type"], "application/octet-stream")
        upload_bytes(settings.minio_processed_bucket, new_key, content, content_type=content_type)

    new_record = {
        "identifier": record["identifier"],
        "title": record["title"],
        "description": record["description"],
        "date": record["date"],
        "body": record["body"],
        "detail_url": record["detail_url"],
        "doc_url": record["doc_url"],
        "partition_date": record["partition_date"],
        "file_type": record["file_type"],
        "file_hash": file_hash,
        "file_path": f"s3://{settings.minio_processed_bucket}/{new_key}",
    }
    return new_record, content_unchanged


def run(start_date: str, end_date: str) -> None:
    landing = get_landing_collection()
    processed = get_processed_collection()
    processed.create_index("identifier", unique=True)
    ensure_bucket(settings.minio_processed_bucket)

    records = list(landing.find({"partition_date": {"$gte": start_date, "$lt": end_date}}))
    log.info("transform_start", extra={"start_date": start_date, "end_date": end_date, "found": len(records)})

    transformed = 0
    skipped_unchanged = 0
    failed = 0
    for record in records:
        try:
            new_record, content_unchanged = transform_record(record, processed)
            processed.update_one({"identifier": new_record["identifier"]}, {"$set": new_record}, upsert=True)
            if content_unchanged:
                skipped_unchanged += 1
                log.info("record_unchanged_skipped", extra={"identifier": record["identifier"]})
            else:
                transformed += 1
                log.info("record_transformed", extra={"identifier": record["identifier"], "file_type": record["file_type"]})
        except Exception as exc:
            failed += 1
            log.error("record_transform_failed", extra={"identifier": record.get("identifier"), "error": repr(exc)})

    log.info(
        "transform_summary",
        extra={
            "start_date": start_date,
            "end_date": end_date,
            "found": len(records),
            "transformed": transformed,
            "skipped_unchanged": skipped_unchanged,
            "failed": failed,
        },
    )


def main():
    parser = argparse.ArgumentParser(description="Clean and re-index landing zone documents into the processed zone.")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD, exclusive")
    args = parser.parse_args()

    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")
    if start >= end:
        parser.error("--start-date must be before --end-date")

    run(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
