from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "wrc_scraper"

SPIDER_MODULES = ["wrc_scraper.spiders"]
NEWSPIDER_MODULE = "wrc_scraper.spiders"

ROBOTSTXT_OBEY = os.environ.get("SCRAPY_ROBOTSTXT_OBEY", "False") == "True"
USER_AGENT = os.environ.get("SCRAPY_USER_AGENT", "wrc_scraper")

CONCURRENT_REQUESTS = int(os.environ.get("SCRAPY_CONCURRENT_REQUESTS", "8"))
DOWNLOAD_DELAY = float(os.environ.get("SCRAPY_DOWNLOAD_DELAY", "0.5"))

AUTOTHROTTLE_ENABLED = os.environ.get("SCRAPY_AUTOTHROTTLE_ENABLED", "True") == "True"
AUTOTHROTTLE_TARGET_CONCURRENCY = float(os.environ.get("SCRAPY_AUTOTHROTTLE_TARGET_CONCURRENCY", "4"))

RETRY_TIMES = int(os.environ.get("SCRAPY_RETRY_TIMES", "3"))
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
