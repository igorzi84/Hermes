import os
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class OpenAIWrapper:
    def __init__(self):
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    # TODO: Implement batch
    def summarize(self, entry) -> str:
        """Summarize a feed entry using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"Check in the RSS feed entries for any breaking changes\
                        or deprecations. Relevant tech stacks are: {os.environ.get('TECH_STACKS')}\
                        If there are any, summarize the changes and provide\
                        a list of the changes and the deadline for the changes. If there are\
                        no changes, return 'No changes found'.",
                    },
                    {
                        "role": "user",
                        "content": f"Title: {entry.title}\nContent: {entry.summary if hasattr(entry, 'summary') else ''}",
                    },
                ],
            )
            logger.debug(f"OpenAI response: {response}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error summarizing entry: {e}")
            return "Error generating summary"
