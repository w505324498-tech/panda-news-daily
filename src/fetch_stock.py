"""Fetch real-time stock index data from Tencent market API.

Returns key Chinese + US index levels for the daily email header.
Free, no API key required.
"""

from __future__ import annotations

import logging
import urllib.request

logger = logging.getLogger(__name__)

# Tencent stock API — GBK-encoded, ~-separated fields.
# Field layout (0-indexed): [1]=name, [3]=current, [4]=prev_close,
# [31]=change_amt, [32]=change_pct
STOCK_API_URL = "http://qt.gtimg.cn/q=sh000001,sz399001,hkHSI,usIXIC"

REQUEST_TIMEOUT = 15
MAX_RETRIES = 2


def _parse_line(line: str) -> dict | None:
    """Parse one Tencent API response line into an index dict."""
    if "=" not in line:
        return None
    _, raw = line.split("=", 1)
    raw = raw.strip().strip('"').rstrip(";")
    fields = raw.split("~")
    if len(fields) < 33:
        return None
    try:
        current = float(fields[3])
        prev_close = float(fields[4])
        change_amt = float(fields[31])
        change_pct = float(fields[32])
    except (ValueError, IndexError):
        return None

    name = fields[1]
    direction = "↑" if change_amt >= 0 else "↓"
    return {
        "name": name,
        "current": current,
        "change_amt": change_amt,
        "change_pct": change_pct,
        "direction": direction,
    }


def fetch_indices() -> list[dict]:
    """Fetch major stock indices. Returns [] on any failure."""
    last_error = ""
    for attempt in range(1 + MAX_RETRIES):
        try:
            req = urllib.request.Request(STOCK_API_URL, headers={
                "User-Agent": "Panda-Intelligence-Center/1.0",
            })
            resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            raw = resp.read()
            text = raw.decode("gbk", errors="replace")
            indices = []
            for line in text.strip().split("\n"):
                parsed = _parse_line(line)
                if parsed:
                    indices.append(parsed)
            if indices:
                logger.info("Stock indices: %d fetched", len(indices))
                return indices
            last_error = "empty response"
        except Exception as e:
            last_error = str(e)
            logger.warning("Stock API attempt %d failed: %s", attempt + 1, e)
        if attempt < MAX_RETRIES:
            import time
            time.sleep(3)
    logger.warning("Stock API all attempts failed: %s", last_error)
    return []
