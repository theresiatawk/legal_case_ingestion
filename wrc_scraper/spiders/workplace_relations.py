from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

import scrapy

from wrc_scraper.items import CaseItem
from wrc_scraper.partitioning import Partition
from wrc_scraper.spiders.base import BaseCaseSpider

BASE_URL = "https://www.workplacerelations.ie/en/search/"
TOTAL_RE = re.compile(r"of\s+(\d+)\s+results", re.IGNORECASE)


class WorkplaceRelationsSpider(BaseCaseSpider):
    name = "workplace_relations"
    allowed_domains = ["workplacerelations.ie"]

    bodies = {
        "equality_tribunal": "1",
        "employment_appeals_tribunal": "2",
        "labour_court": "3",
        "workplace_relations_commission": "15376",
    }

    def build_listing_url(self, body_id: str, partition: Partition, page_number: int) -> str:
        params = {
            "decisions": 1,
            "from": partition.start.strftime("%d/%m/%Y"),
            "to": partition.end.strftime("%d/%m/%Y"),
            "body": body_id,
            "pageNumber": page_number,
        }
        return f"{BASE_URL}?{urlencode(params)}"

    def parse_listing(self, response):
        body = response.meta["body"]
        partition: Partition = response.meta["partition"]
        page_number = response.meta["page_number"]
        key = (body, partition.label)
        stats = self.stats_by_partition[key]

        if page_number == 1:
            header_text = " ".join(t.strip() for t in response.css("div.searchhead::text").getall() if t.strip())
            match = TOTAL_RE.search(header_text)
            stats["site_reported_total"] = int(match.group(1)) if match else None
            self.json_log.info(
                "listing_page_1",
                extra={"body": body, "partition_date": partition.label, "site_reported_total": stats["site_reported_total"]},
            )

        rows = response.css("li.each-item")
        for row in rows:
            identifier = row.css("h2.title a::text").get(default="").strip()
            detail_url = response.urljoin(row.css("h2.title a::attr(href)").get(default=""))
            date_text = row.css("span.date::text").get(default="").strip()
            description = row.css("p.description::attr(title)").get(default="").strip()

            stats["found"] += 1

            yield scrapy.Request(
                detail_url,
                callback=self.parse_detail,
                errback=self.handle_error,
                meta={
                    "body": body,
                    "partition": partition,
                    "identifier": identifier,
                    "date": date_text,
                    "description": description,
                    "detail_url": detail_url,
                },
            )

        next_href = response.css("a.next::attr(href)").get()
        if next_href:
            yield scrapy.Request(
                response.urljoin(next_href),
                callback=self.parse_listing,
                errback=self.handle_error,
                meta={"body": body, "partition": partition, "page_number": page_number + 1},
            )
        elif stats["site_reported_total"] is not None and stats["found"] != stats["site_reported_total"]:
            self.json_log.error(
                "partition_count_mismatch",
                extra={
                    "body": body,
                    "partition_date": partition.label,
                    "found": stats["found"],
                    "site_reported_total": stats["site_reported_total"],
                },
            )

    def parse_detail(self, response):
        download_href = response.css("a.download::attr(href)").get()

        if download_href:
            doc_url = response.urljoin(download_href)
            extension = response.css("p.file-info span.extension::text").get(default="").strip().lower()
            file_type = extension or urlparse(doc_url).path.rsplit(".", 1)[-1].lower()
            yield scrapy.Request(
                doc_url,
                callback=self.parse_document,
                errback=self.handle_error,
                meta={**response.meta, "doc_url": doc_url, "file_type": file_type},
            )
            return

        yield CaseItem(
            identifier=response.meta["identifier"],
            title=response.meta["identifier"],
            description=response.meta["description"],
            date=response.meta["date"],
            body=response.meta["body"],
            detail_url=response.meta["detail_url"],
            partition_date=response.meta["partition"].label,
            doc_url=response.meta["detail_url"],
            file_type="html",
            raw_content=response.body,
        )

    def parse_document(self, response):
        yield CaseItem(
            identifier=response.meta["identifier"],
            title=response.meta["identifier"],
            description=response.meta["description"],
            date=response.meta["date"],
            body=response.meta["body"],
            detail_url=response.meta["detail_url"],
            partition_date=response.meta["partition"].label,
            doc_url=response.meta["doc_url"],
            file_type=response.meta["file_type"],
            raw_content=response.body,
        )
