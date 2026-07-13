# Architecture

## Why monthly partitions

Dates get split into chunks and each chunk is scraped independently. If one chunk fails halfway through, only that one needs re-running, not the whole range. It's also a natural unit for splitting work across workers later, since each partition doesn't depend on any other.

Monthly felt like the right size for the expected volume (roughly 500–1,000 documents). Any bigger and a failure means rerunning a much larger chunk of work. Any smaller and you'd end up making lots of extra search and pagination requests for relatively little gain. But it's not hardcoded `PARTITION_UNIT` and `PARTITION_SIZE` are both env vars, so if this ever needs to run against 1000x the data, dropping to daily partitions is a config change.

## Retries and being polite to the site

Every request (listing pages, case pages, the actual PDF downloads) goes through Scrapy's own downloader, so the same throttling and retry rules apply everywhere. `AUTOTHROTTLE` watches how fast the site is actually responding and backs off if it's struggling, rather than us guessing a fixed delay. Failed requests (429s, 5xx) get retried automatically with Scrapy's built-in backoff.

One thing worth being upfront about: `robots.txt` on this site disallows the `/en/Cases/` path and a few `*_Import/` paths which is basically everything we need to scrape. Respecting that literally would mean the scraper can't work at all. Since this is an academic exercise against a few hundred public legal documents rather than an ongoing production crawl, I chose to disable `ROBOTSTXT_OBEY`.

## How duplicates are avoided

Each case has an identifier (`ADJ-00060622`, `LCR22970`) and that's the unique key in Mongo; records get upserted by identifier, so scraping the same range twice never creates a second copy of anything.

On top of that, every file gets hashed before it's stored. If the hash matches what's already saved, we skip re-uploading it to MinIO, but we still update the Mongo record, because the *metadata* (description, date) can change even when the document itself hasn't.

One unexpected issue was that the site embeds a little HTML comment with a render timestamp in every response (`<!-- Elapsed time: ... -->`). Since this changes on nearly every request, identical pages appeared different until the comment was excluded from the hash calculation.

## If this had to support 50+ sources

Right now there's one spider for one site, but it's already split into two layers: `BaseCaseSpider` handles the stuff that has nothing to do with WRC specifically (partitioning, iterating over bodies, logging, tracking stats) and `WorkplaceRelationsSpider` only knows about the current site's URLs and HTML. The storage pipeline and the transform script don't know anything about the site at all.

So the honest answer for scaling to 50 sources is: add a small config per source (base URL, categories, selectors, pagination rules...) and one subclass of `BaseCaseSpider` per site, and let Dagster run them per-source instead of assuming there's just one.