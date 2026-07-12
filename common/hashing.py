from __future__ import annotations

import hashlib
import re

#workplacerelations.ie injects a server-side render-time comment
#"<!-- Elapsed time: 0.0156022 -->" that changes on every
#request regardless of whether the actual page content changed
#stripped before hashing never from the raw content we actually store
_ELAPSED_TIME_COMMENT_RE = re.compile(rb"<!--\s*Elapsed time:[^>]*-->")


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_html_for_hash(data: bytes) -> bytes:
    return _ELAPSED_TIME_COMMENT_RE.sub(b"", data)
