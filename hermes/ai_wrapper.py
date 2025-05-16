import os
import json
from typing import Dict, Any
import logging
from openai import AsyncOpenAI
import asyncio
import re

logger = logging.getLogger(__name__)


class OpenAIWrapper:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.rate_limit_delay = 0  # Current delay in seconds
        self.max_retries = 3  # Maximum number of retries for rate limit

    async def _handle_rate_limit(self, error_message: str) -> float:
        """Extract wait time from rate limit error and return delay in seconds."""
        try:
            # Extract wait time from error message
            wait_time_match = re.search(r"try again in (\d+\.?\d*)s", error_message)
            if wait_time_match:
                wait_time = float(wait_time_match.group(1))
                # Add a small buffer to the wait time
                return wait_time + 1
            return 30  # Default wait time if we can't parse the message
        except Exception as e:
            logger.error(f"Error parsing rate limit message: {str(e)}")
            return 30  # Default wait time

    async def analyze_entry(self, entry) -> str:
        """Analyze a feed entry using OpenAI."""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # If we have a rate limit delay, wait before making the call
                if self.rate_limit_delay > 0:
                    logger.info(
                        f"Waiting {self.rate_limit_delay} seconds due to rate limit"
                    )
                    await asyncio.sleep(self.rate_limit_delay)
                    self.rate_limit_delay = 0  # Reset the delay

                # Validate API key
                if not os.getenv("OPENAI_API_KEY"):
                    raise ValueError("OpenAI API key is not set")

                # Prepare the entry content
                content = f"Title: {entry.title}\n"
                content += f"Link: {entry.link}\n"
                content += f"Published: {entry.get('published', '')}\n"
                content += f"Summary: {entry.get('summary', '')}\n"
                if "content" in entry:
                    content += f"Content: {entry.content[0].value}\n"

                # Create the system message with explicit JSON structure
                system_message = """You are a feed analyzer that provides structured analysis of feed entries. 
                You should look for retirements, deprecations and breaking changes of the tech stack {breaking_change_targets} only
                and have a deadline or a date that it will happen. If this entry is not related to the tech stack {breaking_change_targets}, you should return an empty JSON object.
                Your response must be a valid JSON object with the following structure:
                {{
                    "summary": "Brief summary of the entry",
                    "deadline": "YYYY-MM-DD" or "No deadline",
                    "impact": "Assessment of impact",
                    "actions": ["List", "of", "required", "actions"],
                    "is_important": true/false
                }}
                
                Rules:
                1. Always include a deadline in YYYY-MM-DD format if one is mentioned
                2. If no deadline is mentioned, then its not important
                3. The deadline must be in the root of the JSON object
                4. Always set is_important to true if the entry requires attention
                5. Provide clear, actionable items in the actions array
                6. Ensure the response is valid JSON""".format(
                    breaking_change_targets=os.environ.get(
                        "BREAKING_CHANGE_TARGETS", ""
                    )
                )

                # Create the user message
                user_message = f"Analyze this feed entry and provide a structured response:\n\n{content}"

                # Get the analysis from OpenAI
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )

                # Extract and return the analysis
                analysis = response.choices[0].message.content.strip()
                logger.debug(f"Raw AI analysis: {analysis}")

                # Validate the response is valid JSON
                try:
                    json.loads(analysis)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response from OpenAI")
                    raise ValueError("Invalid JSON response from OpenAI")

                return analysis

            except Exception as e:
                error_message = str(e)
                if "rate_limit_exceeded" in error_message:
                    retry_count += 1
                    self.rate_limit_delay = await self._handle_rate_limit(error_message)
                    logger.warning(
                        f"Rate limit hit, waiting {self.rate_limit_delay} seconds before retry {retry_count}/{self.max_retries}"
                    )
                    continue
                else:
                    logger.error(f"Error analyzing entry: {error_message}")
                    return json.dumps(
                        {
                            "summary": "Failed to analyze entry due to an error",
                            "deadline": "No deadline",
                            "impact": "Analysis failed",
                            "actions": ["Please review this entry manually"],
                            "is_important": False,
                        }
                    )

        # If we've exhausted all retries, return an error response
        logger.error("Max retries exceeded for rate limit")
        return json.dumps(
            {
                "summary": "Failed to analyze entry due to rate limit",
                "deadline": "No deadline",
                "impact": "Analysis failed",
                "actions": ["Please review this entry manually"],
                "is_important": False,
            }
        )
