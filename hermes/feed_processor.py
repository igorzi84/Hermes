import asyncio
import logging
from typing import List, Dict
import feedparser
import json
import os
import hashlib
from ai_wrapper import OpenAIWrapper
import redis.asyncio as redis
from slack_notifier import SlackNotifier
from pdf_generator import PDFGenerator
import datetime

logger = logging.getLogger(__name__)


class FeedProcessor:
    def __init__(
        self,
        redis_client: redis.Redis,
        slack_notifier: SlackNotifier,
        keywords: List[str] = None,
    ):
        self.redis_client = redis_client
        self.slack_notifier = slack_notifier
        self.ai_wrapper = OpenAIWrapper()
        self.important_entries = []
        self.pdf_generator = PDFGenerator()
        # Get keywords from constructor or environment variable
        self.keywords = keywords or [
            kw.strip()
            for kw in os.getenv("DEFAULT_KEYWORDS", "").split(",")
            if kw.strip()
        ]
        self.total_entries = 0
        logger.info(f"Initialized FeedProcessor with keywords: {self.keywords}")

    async def process_feeds(self, feed_urls: List[str]):
        """Process multiple feeds concurrently."""
        try:
            logger.info(f"Starting to process {len(feed_urls)} feeds")

            # Process all feeds
            tasks = []
            for url in feed_urls:
                logger.info(f"Creating task for feed: {url}")
                task = asyncio.create_task(self.process_feed(url))
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results for any errors
            for url, result in zip(feed_urls, results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing feed {url}: {str(result)}")
                else:
                    logger.info(f"Successfully processed feed: {url}")

            # Log total number of entries
            logger.info(f"Total entries processed from all feeds: {self.total_entries}")

            # After processing all feeds, send a summary notification if there are important entries
            if self.important_entries:
                logger.info(
                    f"Found {len(self.important_entries)} important entries, sending summary notification"
                )
                await self.send_summary_notification()
            else:
                logger.info("No important entries found, skipping summary notification")
        except Exception as e:
            logger.error(f"Error in process_feeds: {str(e)}")
            raise

    async def process_feed(self, feed_url: str):
        """Process a single feed."""
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                # Log detailed parsing issues
                if hasattr(feed, "bozo_exception"):
                    error_msg = str(feed.bozo_exception)
                    if "mismatched tag" in error_msg:
                        logger.warning(
                            f"Feed {feed_url} has XML tag mismatches, attempting to process entries anyway"
                        )
                    else:
                        logger.warning(
                            f"Feed parsing issues for {feed_url}: {error_msg}"
                        )

                # Check if we have any entries despite the parsing issues
                if not feed.entries:
                    logger.error(
                        f"No entries found in feed {feed_url} due to parsing errors"
                    )
                    return
                else:
                    logger.info(
                        f"Found {len(feed.entries)} entries despite parsing issues"
                    )
            self.total_entries += len(feed.entries)
            logger.info(
                f"Successfully parsed feed {feed_url}, found {len(feed.entries)} entries"
            )

            for entry in feed.entries:
                logger.debug(f"Processing entry: {entry.title}")
                logger.debug(f"Entry: {entry}")
                try:
                    await self.process_entry(entry, feed_url)
                except Exception as e:
                    logger.error(f"Error processing entry in feed {feed_url}: {str(e)}")
                    continue  # Continue with next entry even if one fails

        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
            raise  # Re-raise to be caught by process_feeds

    def matches_keywords(self, entry) -> bool:
        """Check if an entry matches any of the configured keywords."""
        if not self.keywords:
            logger.debug("No keywords configured, processing all entries")
            return True  # If no keywords are set, process all entries

        # Combine all text content to search in
        content = f"{entry.title} {entry.get('summary', '')} {entry.get('content', [{'value': ''}])[0].get('value', '')}"
        content = content.lower()

        # Check if any keyword is in the content
        matches = any(keyword.lower() in content for keyword in self.keywords)
        if matches:
            logger.debug(
                f"Entry '{entry.title}' matches keywords: {[k for k in self.keywords if k.lower() in content]}"
            )
        else:
            logger.debug(f"Entry '{entry.title}' does not match any keywords")
        return matches

    async def process_entry(self, entry, feed_url):
        """Process a single feed entry."""
        try:
            # Generate a unique hash for the entry
            entry_hash = self.get_entry_hash(entry)

            # Check if entry has already been processed
            if await self.is_entry_processed(entry_hash):
                logger.debug(
                    f"Skipping already processed entry: {entry.get('title', '')}"
                )
                return

            # Skip if entry doesn't match keywords
            if not self.matches_keywords(entry):
                logger.debug(
                    f"Skipping entry that doesn't match keywords: {entry.get('title', '')}"
                )
                return

            # Analyze the entry using AI
            logger.info(f"{feed_url} - Analyzing entry: {entry.get('title', '')}")
            analysis = await self.ai_wrapper.analyze_entry(entry)

            # Handle analysis data - it could be a string or already a dict
            try:
                if isinstance(analysis, str):
                    analysis_data = json.loads(analysis)
                elif isinstance(analysis, dict):
                    analysis_data = analysis
                else:
                    logger.error(f"Unexpected analysis data type")
                    analysis_data = {"error": "Invalid analysis data type"}

                logger.debug(f"Parsed analysis data: {analysis_data}")

                # Save the entry to Redis with the analysis data
                await self.save_entry(entry_hash, entry, analysis_data, feed_url)

                # If the entry is important, add it to our collection for summary
                if "not_important" not in str(analysis_data).lower():
                    self.important_entries.append(
                        {
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "analysis": analysis_data,
                            "published": entry.get("published", ""),
                            "feed_name": feed_url,  # Add feed name to the entry
                        }
                    )
                    logger.info(
                        f"Added important entry to summary: {entry.get('title', '')}"
                    )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse analysis JSON: {str(e)}")
                # Save the raw analysis string if parsing fails
                await self.save_entry(entry_hash, entry, analysis, feed_url)

        except Exception as e:
            logger.error(f"Error processing entry: {str(e)}")
            raise

    async def send_summary_notification(self):
        """Send a notification to Slack with the report."""
        if not self.important_entries:
            logger.info("No important entries to summarize")
            return

        try:
            # Filter out entries with empty analysis or invalid deadlines
            valid_entries = []
            for entry in self.important_entries:
                try:
                    analysis = entry.get("analysis", {})
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)

                    # Skip entries with empty analysis
                    if not analysis or analysis == {}:
                        logger.debug(
                            f"Skipping entry with empty analysis: {entry.get('title', '')}"
                        )
                        continue

                    # Skip entries with no deadline or invalid deadline
                    deadline = analysis.get("deadline", "No deadline")
                    if deadline == "No deadline":
                        logger.debug(
                            f"Skipping entry with no deadline: {entry.get('title', '')}"
                        )
                        continue

                    try:
                        deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
                        # Skip entries with passed deadlines
                        if deadline_date < datetime.datetime.now():
                            logger.debug(
                                f"Skipping entry with passed deadline: {entry.get('title', '')} - {deadline}"
                            )
                            continue
                    except ValueError:
                        logger.debug(
                            f"Skipping entry with invalid deadline format: {entry.get('title', '')}"
                        )
                        continue

                    valid_entries.append(entry)
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Error processing entry for summary: {str(e)}")
                    continue

            if not valid_entries:
                logger.info("No valid entries to summarize after filtering")
                return

            # Generate PDF report using the consolidated function
            report_path = await self.generate_report(entries=valid_entries)
            if not report_path:
                logger.error("Failed to generate PDF report")
                return

            # Create a copy of the report with a timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_dir = os.path.dirname(report_path)
            report_filename = os.path.basename(report_path)
            saved_report_path = os.path.join(
                report_dir, f"slack_report_{timestamp}_{report_filename}"
            )

            # Copy the file
            import shutil

            shutil.copy2(report_path, saved_report_path)
            logger.info(f"Saved report copy to: {saved_report_path}")

            # Count critical and non-critical events
            critical_count = 0
            non_critical_count = 0
            for entry in valid_entries:
                try:
                    analysis = entry.get("analysis", {})
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)

                    # Check if the entry is critical based on impact or actions
                    impact = analysis.get("impact", "").lower()
                    actions = analysis.get("actions", [])
                    is_critical = any(
                        word in impact for word in ["critical", "urgent", "immediate"]
                    ) or any(
                        word in " ".join(actions).lower()
                        for word in ["critical", "urgent", "immediate"]
                    )

                    if is_critical:
                        critical_count += 1
                    else:
                        non_critical_count += 1
                except (json.JSONDecodeError, AttributeError):
                    non_critical_count += 1

            # Create summary message
            summary = f"*Hermes Feed Analysis Report*\n\n"
            summary += f"*Event Summary:*\n"
            summary += f"• Total Events: {len(valid_entries)}\n"
            summary += f"• Critical Events: {critical_count}\n"
            summary += f"• Non-Critical Events: {non_critical_count}\n\n"
            summary += f"*Important Updates:*\n"

            # Add each important entry
            for entry in valid_entries:
                try:
                    analysis = entry.get("analysis", {})
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)

                    # Determine if entry is critical
                    impact = analysis.get("impact", "").lower()
                    actions = analysis.get("actions", [])
                    is_critical = any(
                        word in impact for word in ["critical", "urgent", "immediate"]
                    ) or any(
                        word in " ".join(actions).lower()
                        for word in ["critical", "urgent", "immediate"]
                    )

                    summary += f"• *{entry['title']}* {'🚨' if is_critical else ''}\n"
                    summary += f"  Summary: {analysis.get('summary', 'No summary available')}\n"
                    summary += (
                        f"  Deadline: {analysis.get('deadline', 'No deadline')}\n"
                    )
                    summary += f"  Impact: {analysis.get('impact', 'Unknown')}\n"
                    summary += f"  Feed: {entry.get('feed_name', 'Unknown Feed')}\n"

                    actions = analysis.get("actions", [])
                    if actions:
                        summary += f"  Actions:\n"
                        for action in actions:
                            summary += f"    - {action}\n"

                    summary += f"  <{entry['link']}|Read more>\n\n"
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Error processing entry for summary: {str(e)}")
                    continue

            # Send the notification with the PDF report
            await self.slack_notifier.send_notification(
                summary, file_path=report_path, file_title="Hermes Feed Analysis Report"
            )
            logger.info("Sent notification with PDF report to Slack")

            # Clear the important entries list after sending
            self.important_entries = []

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            raise

    def get_entry_hash(self, entry) -> str:
        """Generate a unique hash for a feed entry."""
        # Create a string of relevant entry data
        content = f"{entry.title}{entry.link}{entry.get('published', '')}"
        # Use SHA-256 for a consistent hash
        return hashlib.sha256(content.encode()).hexdigest()

    async def is_entry_processed(self, entry_hash: str) -> bool:
        """Check if an entry has been processed before."""
        try:
            is_processed = await self.redis_client.sismember(
                "processed_entries", entry_hash
            )
            if is_processed:
                logger.info(f"Entry with hash {entry_hash} was already processed")
            return is_processed
        except Exception as e:
            logger.error(f"Error checking if entry was processed: {str(e)}")
            return False  # If we can't check Redis, assume it's not processed

    async def save_entry(self, entry_hash: str, entry, analysis: str, feed_url: str):
        """Save entry details and analysis to Redis."""
        # TODO: Add expiration to the entry
        try:
            # Handle analysis data - it could be a string or already a dict
            if isinstance(analysis, str):
                try:
                    analysis_data = json.loads(analysis)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse analysis JSON: {str(e)}")
                    analysis_data = {"error": "Failed to parse analysis"}
            elif isinstance(analysis, dict):
                analysis_data = analysis
            else:
                logger.error(f"Unexpected analysis data type")
                analysis_data = {"error": "Invalid analysis data type"}

            # Store entry details in a hash
            entry_data = {
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "content": entry.get("content", [{"value": ""}])[0].get("value", ""),
                "hash": entry_hash,
                "feed_name": feed_url,  # Add feed name to the entry data
                "analysis": json.dumps(
                    analysis_data
                ),  # Store the analysis data as JSON string
            }

            # Save to Redis using hash
            await self.redis_client.hset(f"entry:{entry_hash}", mapping=entry_data)

            # Add to processed entries set
            await self.redis_client.sadd("processed_entries", entry_hash)

            logger.debug(
                f"Saved entry {entry_hash} to Redis with analysis: {analysis_data}"
            )

        except Exception as e:
            logger.error(f"Error saving entry to Redis: {str(e)}")
            raise

    async def generate_report(
        self, output_filename: str = None, entries: List[Dict] = None
    ) -> str:
        """Generate a PDF report of entries.

        Args:
            output_filename: Optional custom filename for the report
            entries: Optional list of entries to include. If None, fetches all entries from Redis.
        """
        try:
            # If no entries provided, fetch from Redis
            if entries is None:
                # Get all processed entry hashes
                entry_hashes = await self.redis_client.smembers("processed_entries")

                # Fetch all entries from Redis
                entries = []
                for entry_hash in entry_hashes:
                    entry_data = await self.redis_client.hgetall(f"entry:{entry_hash}")
                    if entry_data:
                        # Convert bytes to strings if needed
                        entry_data = {
                            k.decode() if isinstance(k, bytes) else k: (
                                v.decode() if isinstance(v, bytes) else v
                            )
                            for k, v in entry_data.items()
                        }

                        # Handle analysis data - it could be a string or already a dict
                        if "analysis" in entry_data:
                            try:
                                if isinstance(entry_data["analysis"], str):
                                    entry_data["analysis"] = json.loads(
                                        entry_data["analysis"]
                                    )
                                elif isinstance(entry_data["analysis"], dict):
                                    # Already a dict, no need to parse
                                    pass
                                else:
                                    logger.error(
                                        f"Unexpected analysis data type for entry {entry_hash}"
                                    )
                                    continue  # Skip entries with invalid analysis data
                            except json.JSONDecodeError:
                                logger.error(
                                    f"Failed to parse analysis JSON for entry {entry_hash}"
                                )
                                continue  # Skip entries with invalid JSON

                            # Skip entries with empty analysis
                            if (
                                not entry_data["analysis"]
                                or entry_data["analysis"] == {}
                            ):
                                logger.debug(
                                    f"Skipping entry {entry_hash} with empty analysis"
                                )
                                continue

                            # Skip entries with no deadline or invalid deadline
                            deadline = entry_data["analysis"].get(
                                "deadline", "No deadline"
                            )
                            if deadline == "No deadline":
                                logger.debug(
                                    f"Skipping entry {entry_hash} with no deadline"
                                )
                                continue

                            try:
                                deadline_date = datetime.datetime.strptime(
                                    deadline, "%Y-%m-%d"
                                )
                                # Skip entries with passed deadlines
                                if deadline_date < datetime.datetime.now():
                                    logger.debug(
                                        f"Skipping entry {entry_hash} with passed deadline: {deadline}"
                                    )
                                    continue
                            except ValueError:
                                logger.debug(
                                    f"Skipping entry {entry_hash} with invalid deadline format"
                                )
                                continue

                            entries.append(entry_data)

            if not entries:
                logger.warning("No entries found to generate report")
                return None

            # Sort entries by deadline
            def get_deadline(entry):
                try:
                    analysis = entry.get("analysis", {})
                    if isinstance(analysis, str):
                        analysis = json.loads(analysis)
                    deadline = analysis.get("deadline", "No deadline")
                    if deadline == "No deadline":
                        return datetime.datetime.max
                    return datetime.datetime.strptime(deadline, "%Y-%m-%d")
                except (ValueError, json.JSONDecodeError):
                    return datetime.datetime.max

            entries.sort(key=get_deadline)

            # Generate the PDF report
            report_path = self.pdf_generator.generate_report(entries, output_filename)
            logger.info(f"Generated PDF report: {report_path}")
            return report_path

        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            raise

    async def generate_summary_report(self, output_filename: str = None) -> str:
        """Generate a summary report of all entries."""
        try:
            # Get all processed entry hashes
            entry_hashes = await self.redis_client.smembers("processed_entries")
            if not entry_hashes:
                logger.warning("No entries found in Redis")
                return None

            # Fetch all entries
            entries = []
            for entry_hash in entry_hashes:
                entry_data = await self.redis_client.hgetall(f"entry:{entry_hash}")
                if entry_data:
                    entries.append(entry_data)

            if not entries:
                logger.warning("No entries found in Redis")
                return None

            # Generate the summary report
            report_path = self.pdf_generator.generate_summary_report(
                entries, output_filename
            )
            logger.info(f"Generated summary report: {report_path}")
            return report_path

        except Exception as e:
            logger.error(f"Error generating summary report: {str(e)}")
            raise
