from __future__ import annotations

import os
from datetime import datetime

import scrapy

from common.logging_utils import get_logger
from wrc_scraper.partitioning import Partition, generate_partitions


class BaseCaseSpider(scrapy.Spider):
    #This architecture assumes all sources follow a common pattern:Listing page that contains many case links, Detail page for each case

    bodies: dict[str, str] = {}

    def __init__(self, start_date: str, end_date: str, bodies: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        self.selected_bodies = bodies.split(",") if bodies else list(self.bodies.keys())
        self.partition_unit = os.environ.get("PARTITION_UNIT", "months")
        self.partition_size = int(os.environ.get("PARTITION_SIZE", "1"))
        self.json_log = get_logger(self.name)
        self.stats_by_partition: dict[tuple[str, str], dict] = {}

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        partitions = generate_partitions(self.start_date, self.end_date, self.partition_unit, self.partition_size)
        for body_name in self.selected_bodies:
            body_id = self.bodies[body_name]
            for partition in partitions:
                key = (body_name, partition.label)
                self.stats_by_partition[key] = {"found": 0, "scraped": 0, "failed": 0, "site_reported_total": None}
                self.json_log.info("partition_start", extra={"body": body_name, "partition_date": partition.label})
                url = self.build_listing_url(body_id, partition, page_number=1)
                yield scrapy.Request(
                    url,
                    callback=self.parse_listing,
                    errback=self.handle_error,
                    meta={"body": body_name, "partition": partition, "page_number": 1},
                )

    def build_listing_url(self, body_id: str, partition: Partition, page_number: int) -> str:
        raise NotImplementedError

    def parse_listing(self, response):
        raise NotImplementedError

    def handle_error(self, failure):
        request = failure.request
        body = request.meta.get("body")
        partition: Partition | None = request.meta.get("partition")
        key = (body, partition.label) if partition else None
        if key in self.stats_by_partition:
            self.stats_by_partition[key]["failed"] += 1
        self.json_log.error(
            "request_failed",
            extra={
                "url": request.url,
                "body": body,
                "partition_date": partition.label if partition else None,
                "error": repr(failure.value),
            },
        )

    def closed(self, reason):
        summary = [
            {"body": body, "partition_date": partition_date, **counts}
            for (body, partition_date), counts in sorted(self.stats_by_partition.items())
        ]
        self.json_log.info("run_summary", extra={"reason": reason, "partitions": summary})
