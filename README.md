# Legal Case Ingestion

This scrapes case law from Ireland's [Workplace Relations Commission](https://www.workplacerelations.ie) site (the Labour Court, the Equality Tribunal, and the Employment Appeals Tribunal) and saves both the documents and their metadata somewhere useful.

The flow is: scrape into a "landing zone" (raw files in MinIO, metadata in Mongo), then a separate transform step cleans that up into a "processed zone" (HTML gets stripped down to just the actual decision text, everything gets renamed to its case identifier). Dagster ties the two steps together so transform only runs once scraping is actually done.

Why it's built this way — partition sizes, retries, how duplicates are avoided, what would need to change to add more sites — is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Before you start

You'll need Python 3.12 and Docker Desktop running. (Python 3.12 specifically — Scrapy's underlying Twisted library tends to lag behind the newest Python releases, so something like 3.14 can cause install headaches.)

## Getting it running

Clone the repo, then set up a virtual environment:

```
python -m venv .venv
```

Activate it — `.venv\Scripts\Activate.ps1` on PowerShell, or `source .venv/Scripts/activate` in Git Bash — and install everything:

```
pip install -r requirements.txt
```

Copy `.env.example` to `.env`. Most of the values in there are your call, but here's a set that's known to work:

```
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=changeme123
MONGO_PORT=27018
MONGO_URI=mongodb://admin:changeme123@localhost:27018/?authSource=admin
MONGO_DB=legal_case_ingestion
MONGO_LANDING_COLLECTION=cases_landing
MONGO_PROCESSED_COLLECTION=cases_processed

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_ENDPOINT=http://localhost:9000
MINIO_LANDING_BUCKET=landing-zone
MINIO_PROCESSED_BUCKET=processed-zone

PARTITION_UNIT=months
PARTITION_SIZE=1

SCRAPY_ROBOTSTXT_OBEY=False
SCRAPY_USER_AGENT=LegalCaseIngestionAcademicBot/1.0
SCRAPY_CONCURRENT_REQUESTS=8
SCRAPY_DOWNLOAD_DELAY=0.5
SCRAPY_AUTOTHROTTLE_ENABLED=True
SCRAPY_RETRY_TIMES=3
```

Then bring up the containers:

```
docker compose up -d
```

That starts Mongo and MinIO, plus two small web UIs if you want to poke around the data by eye:
- Mongo Express at http://localhost:8081
- MinIO Console at http://localhost:9001

## Scraping

```
scrapy crawl workplace_relations -a start_date=2024-01-01 -a end_date=2024-07-01
```

`start_date`/`end_date` are `YYYY-MM-DD`, with the end date not included in the range. There's also an optional `bodies` argument if you only want one or two of the four sources e.g. `-a bodies=labour_court`.

## Transforming

```
python -m transform.transform --start-date 2024-01-01 --end-date 2024-07-01
```

This pulls whatever's in the landing zone for that range, leaves PDFs and Word docs untouched, and for HTML pages strips away the header/nav/footer boilerplate so only the actual decision text remains. Everything gets renamed to `<identifier>.<ext>` and written to a separate processed bucket and Mongo collection. The landing zone itself is never touched.

## Running both together with Dagster

Instead of running the two commands above by hand, Dagster can chain them — transform only kicks off once scraping has actually finished successfully.

```
dagster dev -f orchestration/dagster_project/definitions.py
```

That opens a UI at http://localhost:3000. Launch `scrape_and_transform_job` from there and give it some run config (there's an example at `orchestration/dagster_project/run_config.example.yaml`)

Or, if you'd rather skip the UI and just fire it off from the terminal:

```
dagster job execute -f orchestration/dagster_project/definitions.py -j scrape_and_transform_job -c orchestration/dagster_project/run_config.example.yaml
```