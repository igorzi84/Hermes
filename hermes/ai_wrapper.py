import os
import json
from typing import Dict, Any
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIWrapper:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    async def analyze_entry(self, entry) -> str:
        """Analyze a feed entry using OpenAI."""
        try:
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
            You should look for retirements, deprecations and breaking changes of the tech stack {tech_stack} 
            and have a deadline or a date that it will happen.
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
                tech_stack=os.environ.get("TECH_STACKS", "")
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

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            return json.dumps(
                {
                    "summary": f"Analysis failed: {str(ve)}",
                    "deadline": "No deadline",
                    "impact": "Analysis failed",
                    "actions": ["Please review this entry manually"],
                    "is_important": False,
                }
            )
        except Exception as e:
            logger.error(f"Error analyzing entry: {str(e)}")
            return json.dumps(
                {
                    "summary": "Failed to analyze entry due to an error",
                    "deadline": "No deadline",
                    "impact": "Analysis failed",
                    "actions": ["Please review this entry manually"],
                    "is_important": False,
                }
            )
