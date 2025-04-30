import feedparser
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def search_feed_for_keywords(feed_url, keywords):
    """
    Search RSS feed for specific keywords in titles and summaries.

    Args:
        feed_url (str): URL of the RSS feed
        keywords (list): List of keywords to search for
    """
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        logger.warning("No entries found in the feed")
        return
    logger.info(f"Feed: {feed.feed.title}")
    logger.info(f"Searching for keywords: {', '.join(keywords)}")
    logger.info(f"Found {len(feed.entries)} entries in the feed")

    for entry in feed.entries:
        title = entry.title.lower()
        summary = entry.summary.lower()

        # Check if any keyword is in title or summary
        if any(
            keyword.lower() in title or keyword.lower() in summary
            for keyword in keywords
        ):
            print("\n" + "=" * 80)
            print(f"Title: {entry.title}")
            print(f"Link: {entry.link}")
            print(f"Published: {entry.published}")
            print("-" * 40)
            print(f"Summary: {entry.summary}")
            print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <keyword1> [keyword2] [keyword3] ...")
        sys.exit(1)

    keywords = sys.argv[1:]
    feed_url = [
        "https://www.microsoft.com/releasecommunications/api/v2/azure/rss",
        "https://aws.amazon.com/blogs/aws/feed/",
    ]
    for f in feed_url:
        search_feed_for_keywords(f, keywords)
