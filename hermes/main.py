import asyncio
import argparse
import logging
import os
from dotenv import load_dotenv
from feed_processor import FeedProcessor
import redis.asyncio as redis
from slack_notifier import SlackNotifier
import sys

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    # Get default keywords from .env
    default_keywords = os.getenv("DEFAULT_KEYWORDS", "")
    default_keywords = (
        [kw.strip() for kw in default_keywords.split(",")] if default_keywords else []
    )

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
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate a PDF report of all processed entries",
    )
    parser.add_argument(
        "--report-filename",
        help="Specify a custom filename for the PDF report",
    )

    return parser.parse_args()


async def main():
    # Parse command line arguments
    args = parse_arguments()

    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize Redis client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

    # Initialize Slack notifier
    slack_notifier = SlackNotifier()

    # Initialize feed processor
    feed_processor = FeedProcessor(
        redis_client=redis_client, slack_notifier=slack_notifier, keywords=args.keywords
    )

    try:
        if args.generate_report:
            logger.info("Generating PDF report...")
            report_path = await feed_processor.generate_report(args.report_filename)
            if report_path:
                logger.info(f"Report generated successfully: {report_path}")
            else:
                logger.warning("No entries found to generate report")
        else:
            # Get feeds from command line or environment variable
            feeds = (
                args.feeds.split(",")
                if args.feeds
                else os.getenv("RSS_FEEDS", "").split(",")
            )
            if not feeds or not feeds[0]:
                print(
                    "No RSS feeds configured. Please set RSS_FEEDS environment variable or use --feeds option."
                )
                return

            # List feeds if requested
            if args.list_feeds:
                print("\nConfigured RSS Feeds:")
                for feed in feeds:
                    print(f"- {feed}")
                return

            # Process feeds
            logger.info(
                f"Processing {len(feeds)} feeds with the following keywords: {args.keywords}"
            )
            await feed_processor.process_feeds(feeds)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
