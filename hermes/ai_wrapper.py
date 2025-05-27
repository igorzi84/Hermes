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
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY key is not set")
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.rate_limit_delay = 0  # Current delay in seconds
        self.max_retries = 3  # Maximum number of retries for rate limit
        self.max_content_length = (
            4000  # Maximum length for content to avoid context window issues
        )

    def _truncate_content(self, content: str) -> str:
        """Truncate content to fit within the model's context window."""
        if len(content) > self.max_content_length:
            logger.warning(
                f"Content length {len(content)} exceeds maximum {self.max_content_length}, truncating..."
            )
            # Truncate to max length, but try to end at a sentence
            truncated = content[: self.max_content_length]
            last_period = truncated.rfind(".")
            if last_period > 0:
                truncated = truncated[: last_period + 1]
            return truncated + "\n[Content truncated due to length]"
        return content

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

                # Prepare the entry content
                content = f"Title: {entry.title}\n"
                content += f"Link: {entry.link}\n"
                content += f"Published: {entry.get('published', '')}\n"

                # Get and truncate summary
                summary = entry.get("summary", "")
                content += f"Summary: {self._truncate_content(summary)}\n"

                # Get and truncate content if available
                if "content" in entry:
                    content_value = entry.content[0].value
                    content += f"Content: {self._truncate_content(content_value)}\n"

                # Create the system message with explicit JSON structure
                system_message = """You are a feed analyzer that provides structured analysis of feed entries. 
You should only look for retirements, deprecations, and breaking changes that affect the tech stack {breaking_change_targets}.

If the entry is NOT related to the tech stack {breaking_change_targets}, you MUST return an empty JSON object — even if there is a breaking change or deadline.

If the entry IS related to the tech stack and includes a retirement, deprecation, or breaking change, then provide a response in the following JSON format:
{{
    "summary": "Brief summary of the entry",
    "deadline": "YYYY-MM-DD" or "No deadline",
    "impact": "Assessment of impact",
    "actions": ["List", "of", "required", "actions"],
    "is_important": true/false,
    "reasoning": "Explain why you added this entry and not returned empty json"
}}

Rules:
1. If no deadline is mentioned in the source, set "deadline" to "No deadline"
2. If no deadline is mentioned, set "is_important" to false
3. Do not return anything if the entry is unrelated to {breaking_change_targets}
4. Ensure "is_important" is true only if the entry requires action and affects the stack
5. Provide actionable steps in the actions array
6. The response must be valid JSON""".format(
                    breaking_change_targets=os.environ.get(
                        "BREAKING_CHANGE_TARGETS", ""
                    )
                )

                # Create the user message
                user_message = f"Analyze this feed entry and provide a structured response:\n\n{content}"

                # Get the analysis from OpenAI
                response = await self.client.chat.completions.create(
                    model=self.model,
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
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from OpenAI: {str(e)}")
                    logger.error(f"Raw response: {analysis}")
                    raise ValueError("Invalid JSON response from OpenAI") from e

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
