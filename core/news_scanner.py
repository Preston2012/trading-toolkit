"""News headline scanner with hash-based deduplication.

Scans Finnhub general news for relevant headlines, matches them
against a keyword-to-trade map, and deduplicates using MD5 hashes
persisted to a JSON file.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import TypedDict

logger = logging.getLogger(__name__)

MAX_SEEN_ENTRIES = 500


class NewsSignal(TypedDict):
    """A matched news signal with suggested trade."""

    headline: str
    play: str
    logic: str
    hash: str


def get_seen(seen_file: str) -> dict[str, str]:
    """Load previously seen headline hashes from disk.

    Args:
        seen_file: Path to the JSON file storing seen hashes.

    Returns:
        Dict mapping hash -> ISO timestamp.
    """
    if os.path.exists(seen_file):
        with open(seen_file) as f:
            return json.load(f)
    return {}


def save_seen(seen: dict[str, str], seen_file: str) -> None:
    """Persist seen headline hashes to disk.

    Trims to most recent entries if the dict exceeds MAX_SEEN_ENTRIES.

    Args:
        seen: Dict mapping hash -> ISO timestamp.
        seen_file: Path to the JSON file.
    """
    if len(seen) > MAX_SEEN_ENTRIES:
        items = sorted(seen.items(), key=lambda x: x[1], reverse=True)[:MAX_SEEN_ENTRIES]
        seen = dict(items)
    os.makedirs(os.path.dirname(seen_file) or ".", exist_ok=True)
    with open(seen_file, "w") as f:
        json.dump(seen, f)


def scan_news(
    finnhub_key: str,
    seen_file: str,
    trade_map: dict[str, tuple[str, str]],
    source_keywords: list[str] | None = None,
) -> list[NewsSignal]:
    """Scan Finnhub news for actionable headlines.

    Fetches general news, filters by source keywords, matches against
    the trade map, and deduplicates using MD5 hashes.

    Args:
        finnhub_key: Finnhub API key.
        seen_file: Path to the seen headlines JSON file.
        trade_map: Keyword -> (play, logic) mapping.
        source_keywords: Headlines must contain at least one of these
            (default: ["trump", "truth social", "president said", "white house"]).

    Returns:
        List of new NewsSignal dicts.
    """
    if source_keywords is None:
        source_keywords = ["trump", "truth social", "president said", "white house"]

    seen = get_seen(seen_file)
    signals: list[NewsSignal] = []

    try:
        import finnhub
        client = finnhub.Client(api_key=finnhub_key)
        news = client.general_news("general", min_id=0)

        for article in news[:50]:
            headline = article.get("headline", "")
            h_hash = hashlib.md5(headline.encode()).hexdigest()[:12]

            if h_hash in seen:
                continue

            headline_lower = headline.lower()
            if not any(kw in headline_lower for kw in source_keywords):
                continue

            for keyword, (play, logic) in trade_map.items():
                if keyword in headline_lower:
                    signals.append(NewsSignal(
                        headline=headline[:120],
                        play=play,
                        logic=logic,
                        hash=h_hash,
                    ))
                    seen[h_hash] = datetime.now().isoformat()
                    break

    except Exception as exc:
        logger.warning("News scan error: %s", exc)

    save_seen(seen, seen_file)
    return signals
