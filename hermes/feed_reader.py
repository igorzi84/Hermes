import feedparser
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FeedReader:
    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    async def fetch_feed(self) -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch feed {self.feed_url}: HTTP {response.status}"
                    )
                    return []

                return await response.text()

    async def search_feed_for_keywords(self, keywords: list[str]) -> list[dict]:
        feed = await self.fetch_feed()
        content = feedparser.parse(feed)
        found_entries = []

        if not content:
            logger.warning(f"No entries found in the feed: {self.feed_url}")
            return []

        if hasattr(content.feed, "title"):
            logger.info(f"Feed: {content.feed.title}")
        else:
            logger.info(f"Feed: {self.feed_url}")

        for entry in content.entries:
            title = entry.title.lower()
            summary = entry.summary.lower() if hasattr(entry, "summary") else ""

            # Check if any keyword is in title or summary
            if any(
                keyword.lower() in title or keyword.lower() in summary
                for keyword in keywords
            ):
                found_entries.append(entry)

        return found_entries
