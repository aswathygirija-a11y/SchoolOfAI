import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

DEFAULT_FEED_HOSTS = (
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
)

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _entry_date_iso(entry: Any) -> str:
    if getattr(entry, "published_parsed", None):
        t = entry.published_parsed
        try:
            dt = datetime(*t[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    return getattr(entry, "published", None) or getattr(entry, "updated", "") or ""


def _feed_urls(username: str, feed_url: str | None) -> list[str]:
    if feed_url:
        return [feed_url]
    return [f"{host}/twitter/user/{username}" for host in DEFAULT_FEED_HOSTS]


def fetch_latest(username: str, limit: int, feed_url: str | None) -> list[dict[str, Any]]:
    headers = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    urls = _feed_urls(username, feed_url)
    last_error: str | None = None
    response: httpx.Response | None = None
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=headers) as client:
        for url in urls:
            try:
                r = client.get(url)
                r.raise_for_status()
                response = r
                break
            except httpx.HTTPStatusError as exc:
                last_error = f"{exc.request.url}: HTTP {exc.response.status_code}"
            except httpx.RequestError as exc:
                last_error = f"{url}: {exc.__class__.__name__}: {exc}"

    if response is None:
        raise RuntimeError(
            "Could not fetch any RSS feed. Tried:\n  - "
            + "\n  - ".join(urls)
            + (f"\nLast error: {last_error}" if last_error else "")
            + "\nInstall deps: pip install -r requirements.txt\n"
            "Or pass a working Atom/RSS URL: --feed-url YOUR_RSS_URL"
        )

    parsed = feedparser.parse(response.content)
    if not parsed.entries:
        hint = ""
        if parsed.bozo and getattr(parsed, "bozo_exception", None):
            hint = f" ({parsed.bozo_exception})"
        raise ValueError(f"No entries in feed from {response.url}{hint}")

    tweets: list[dict[str, Any]] = []
    for entry in parsed.entries[:limit]:
        link = getattr(entry, "link", "") or ""
        tweet_id = ""
        if link:
            path = urlparse(link).path.strip("/").split("/")
            if path:
                tweet_id = path[-1]
        summary = getattr(entry, "summary", None) or getattr(entry, "title", "") or ""
        text = summary
        if "<" in text and ">" in text:
            text = re.sub(r"<[^>]+>", " ", text)
            text = " ".join(text.split())
        tweets.append(
            {
                "id": tweet_id or getattr(entry, "id", ""),
                "date_utc": _entry_date_iso(entry),
                "url": link,
                "content": text,
                "likes": None,
                "retweets": None,
                "replies": None,
            }
        )
    return tweets


def print_tweets(tweets: list[dict]) -> None:
    if not tweets:
        print("No tweets found.")
        return

    for idx, tweet in enumerate(tweets, start=1):
        print(f"\n{idx}. {tweet['url']}")
        print(f"   Date (UTC): {tweet['date_utc']}")
        stats = tweet.get("likes")
        if stats is not None:
            print(
                f"   Stats: {tweet['likes']} likes | "
                f"{tweet['retweets']} reposts | {tweet['replies']} replies"
            )
        print(f"   Text: {tweet['content']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get Andrej Karpathy's latest tweets/posts (via RSS)."
    )
    parser.add_argument("--limit", type=int, default=5, help="Number of latest tweets")
    parser.add_argument(
        "--username",
        default="karpathy",
        help="X/Twitter username to fetch from (default: karpathy)",
    )
    parser.add_argument(
        "--feed-url",
        default=None,
        help="Override RSS/Atom feed URL (default: RSSHub twitter user feed)",
    )
    parser.add_argument(
        "--save-json",
        default="karpathy_latest_tweets.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 1

    try:
        tweets = fetch_latest(args.username, args.limit, args.feed_url)
        print_tweets(tweets)

        output = {
            "username": args.username,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "count": len(tweets),
            "tweets": tweets,
        }
        out_path = Path(args.save_json)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved {len(tweets)} tweets to: {out_path}")
    except (RuntimeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write JSON: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
