import os
import json
import logging
import aiohttp
from typing import List
from dotenv import load_dotenv
from slack_sdk.web.async_client import AsyncWebClient

load_dotenv()

logger = logging.getLogger(__name__)


class SlackNotifier:
    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is not set")

        self.channel = os.getenv("SLACK_CHANNEL", "#general")
        self.client = AsyncWebClient(token=self.token)

    async def send_notification(
        self, message: str, file_path: str = None, file_title: str = None
    ):
        """Send a notification to Slack with optional file attachment."""
        try:
            # Prepare the message blocks
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message}}]

            # Prepare the message payload
            payload = {
                "channel": self.channel,
                "blocks": blocks,
                "text": message,  # Fallback text
            }

            # If a file is provided, upload it first
            if file_path and os.path.exists(file_path):
                try:
                    # Upload the file
                    with open(file_path, "rb") as file:
                        response = await self.client.files_upload_v2(
                            channel=self.channel,
                            file=file,
                            title=file_title or "Report",
                            initial_comment="Here's the detailed report:",
                        )
                        if not response["ok"]:
                            logger.error(
                                f"Failed to upload file to Slack: {response.get('error', 'Unknown error')}"
                            )
                except Exception as e:
                    logger.error(f"Error uploading file to Slack: {str(e)}")
            else:
                # Send just the message if no file
                response = await self.client.chat_postMessage(**payload)

            if not response["ok"]:
                logger.error(
                    f"Failed to send notification to Slack: {response.get('error', 'Unknown error')}"
                )
                return False

            logger.info("Successfully sent notification to Slack")
            return True

        except Exception as e:
            logger.error(f"Error sending notification to Slack: {str(e)}")
            return False

    async def send_notification_with_file(
        self,
        title: str,
        source_url: str,
        summary: str,
        severity: str = "info",
        actions: List[str] = None,
        file_path: str = None,
        file_title: str = None,
    ):
        """Send a notification to Slack with an optional file attachment."""
        try:
            # Format the message according to Slack's block kit
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{title}*\n\n{summary}"},
                }
            ]

            # Add source URL if provided
            if source_url:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"<{source_url}|View Source>",
                        },
                    }
                )

            # Add actions if provided
            if actions:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Recommended Actions:*\n"
                            + "\n".join(f"• {action}" for action in actions),
                        },
                    }
                )

            # Add severity indicator
            severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
                severity.lower(), "ℹ️"
            )

            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"{severity_emoji} *{severity.upper()}*",
                        }
                    ],
                }
            )
            logger.info(f"Sending Slack notification: {blocks}")
            # Prepare the payload
            payload = {
                "blocks": blocks,
                "text": title,  # Fallback text for notifications
            }

            # If a file is provided, upload it first
            if file_path and os.path.exists(file_path):
                try:
                    # Upload the file
                    with open(file_path, "rb") as file:
                        response = await self.client.files_upload_v2(
                            channel=self.channel,
                            file=file,
                            title=file_title or "Report",
                            initial_comment="Here's the detailed report:",
                        )
                        if not response["ok"]:
                            logger.error(
                                f"Failed to upload file to Slack: {response.get('error', 'Unknown error')}"
                            )
                except Exception as e:
                    logger.error(f"Error uploading file to Slack: {str(e)}")
            else:
                # Send just the message if no file
                response = await self.client.chat_postMessage(**payload)

            if not response["ok"]:
                logger.error(
                    f"Failed to send notification to Slack: {response.get('error', 'Unknown error')}"
                )
                return False

            logger.info("Successfully sent notification to Slack")
            return True

        except Exception as e:
            logger.error(f"Error sending notification to Slack: {str(e)}")
            return False
