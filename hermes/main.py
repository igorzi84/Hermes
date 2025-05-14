import argparse
import hashlib
import logging
import os
import sys

import redis.asyncio as redis
from dotenv import load_dotenv

from ai_wrapper import OpenAIWrapper
from feed_reader import FeedReader

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True,
)


def parse_arguments():
    """Parse command line arguments."""
    # Get default keywords from .env
    default_keywords = os.getenv("DEFAULT_KEYWORDS")
    default_keywords = [kw.strip() for kw in default_keywords.split(",")]

    parser = argparse.ArgumentParser(
        description="Search RSS feeds for specific keywords."
    )
    parser.add_argument(
        "keywords",
        nargs="*",
        default=default_keywords,
        help="Keywords to search for in RSS feeds",
    )
    parser.add_argument(
        "--feeds", "-f", help="Comma-separated list of RSS feed URLs (overrides .env)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--list-feeds",
        action="store_true",
        help="List the configured RSS feeds and exit",
    )

    return parser.parse_args()


async def get_entry_hash(entry) -> str:
    """Generate a unique hash for a feed entry based on its content."""
    # Create a string of relevant entry data
    entry_data = f"{entry.title}{entry.link}{entry.published if hasattr(entry, 'published') else ''}"
    return hashlib.sha256(entry_data.encode()).hexdigest()


async def is_entry_processed(entry_hash: str) -> bool:
    """Check if an entry has been processed before using Redis."""
    return await redis_client.sismember("processed_entries", entry_hash)


async def save_entry(entry_hash: str, entry, ai_summary: str):
    """Save entry details to Redis."""
    # Store entry details in a hash
    entry_data = {
        "title": entry.title,
        "link": entry.link,
        "published": entry.published if hasattr(entry, "published") else "",
        "summary": entry.summary if hasattr(entry, "summary") else "",
        "content": (
            entry.content[0].value
            if hasattr(entry, "content") and entry.content
            else ""
        ),
        "hash": entry_hash,
        "ai_summary": ai_summary,
    }

    # Save to Redis using hash
    await redis_client.hset(f"entry:{entry_hash}", mapping=entry_data)

    # Add to processed entries set
    await redis_client.sadd("processed_entries", entry_hash)


async def get_entry(entry_hash: str) -> dict:
    """Retrieve entry details from Redis."""
    return await redis_client.hgetall(f"entry:{entry_hash}")


async def search_feed(feed_url: str, keywords: list[str]):
    feed_reader = FeedReader(feed_url)
    return await feed_reader.search_feed_for_keywords(keywords)


async def main():
    args = parse_arguments()
    ai_wrapper = OpenAIWrapper()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    # Get feed URLs from arguments or environment
    if args.feeds:
        feed_urls = [url.strip() for url in args.feeds.split(",")]
        logger.info(f"Using {len(feed_urls)} feed URLs from command line")
    else:
        feed_urls_str = os.getenv("RSS_FEEDS")
        if feed_urls_str:
            feed_urls = [url.strip() for url in feed_urls_str.split(",")]
            logger.info(f"Loaded {len(feed_urls)} feed URLs from .env file")
        else:
            logger.warning("No RSS_FEEDS found in .env file, using defaults")
            feed_urls = [
                "https://aws.amazon.com/blogs/aws/feed/",
            ]

    # List feeds if requested
    if args.list_feeds:
        logger.info("Configured RSS feeds:")
        for i, url in enumerate(feed_urls, 1):
            logger.info(f"{i}. {url}")
        sys.exit(0)

    # Process each feed concurrently
    tasks = [search_feed(feed_url, args.keywords) for feed_url in feed_urls]
    results = await asyncio.gather(*tasks)

    for feed_url, found_entries in zip(feed_urls, results):
        if found_entries:
            logger.info(f"Found {len(found_entries)} entries in {feed_url}")

            for entry in found_entries:
                entry_hash = await get_entry_hash(entry)

                # Skip if we've already processed this entry
                if await is_entry_processed(entry_hash):
                    logger.debug(f"Skipping already processed entry: {entry.title}")
                    continue

                logger.info(f"Title: {entry.title}")
                logger.info(f"Link: {entry.link}")
                logger.info(
                    f"Published: {entry.published if hasattr(entry, 'published') else 'N/A'}"
                )
                logger.info("-" * 40)

                summary = ai_wrapper.summarize(entry)
                logger.info(f"Summary: {summary}")

                # Save entry to Redis
                await save_entry(entry_hash, entry, summary)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
