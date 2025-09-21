import json
import logging
from typing import Any, Dict

from openai import OpenAI

from .base import ParserError, ParseResult, TaskParser

logger = logging.getLogger(__name__)


class OpenAITaskParser(TaskParser):
    """OpenAI implementation of task text parser."""

    def _setup(self) -> None:
        """Setup OpenAI client."""
        if not self.config.api_key:
            raise ParserError("OpenAI API key is required")

        try:
            self.client = OpenAI(api_key=self.config.api_key)
            logger.info(
                f"OpenAI task parser initialized with model: {self.config.model}"
            )
        except Exception as e:
            raise ParserError(f"Failed to initialize OpenAI client: {str(e)}")

    def parse_text(self, text: str) -> ParseResult:
        """Parse natural language text into structured task data using OpenAI."""
        self._validate_text(text)

        try:
            logger.info(f"Parsing task text with OpenAI: {text[:100]}...")

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": self._build_parsing_prompt(text)},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            response_text = response.choices[0].message.content
            if not response_text:
                raise ParserError("OpenAI returned empty response")

            parsed_data = self._parse_ai_response(response_text.strip())
            result = self._build_parse_result(text, parsed_data)

            logger.info(
                f"Successfully parsed task: '{result.title}' (confidence: {result.confidence_score:.2f})"
            )

            return result

        except ParserError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse task text: {str(e)}")
            raise ParserError(f"OpenAI parsing error: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for OpenAI."""
        return (
            "You are an expert project management assistant that parses natural language "
            "text into structured task data. Your job is to extract key information from "
            "user input and format it as a JSON object.\n\n"
            "Guidelines:\n"
            "- Extract a clear, concise title (max 100 characters)\n"
            "- Create a detailed description based on the input\n"
            "- Identify priority: low, medium, high, urgent\n"
            "- Extract time estimates if mentioned (convert to story points: 1-2h=1, 3-6h=2, 1day=3, etc.)\n"
            "- Identify task type: task, bug, feature, story, epic\n"
            "- Extract due dates if mentioned (format: YYYY-MM-DD)\n"
            "- Extract relevant tags/keywords\n"
            "- Provide confidence score (0.0-1.0) for parsing accuracy\n\n"
            "Always respond with valid JSON format as requested."
        )

    def _build_parsing_prompt(self, text: str) -> str:
        """Build the parsing prompt for the given text."""
        return f"""
Please parse the following task description into structured data:

"{text}"

Respond with a JSON object containing:
{{
    "title": "Clear, concise task title",
    "description": "Detailed task description",
    "priority": "low|medium|high|urgent",
    "estimate": null or number (story points),
    "due_date": null or "YYYY-MM-DD",
    "task_type": "task|bug|feature|story|epic",
    "tags": ["tag1", "tag2"],
    "confidence_score": 0.0-1.0,
    "reasoning": "Brief explanation of parsing decisions"
}}
"""

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate AI response."""
        try:
            parsed_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {response_text}")
            raise ParserError(f"Invalid JSON response from AI: {str(e)}")

        # Validate required fields
        required_fields = ["title", "description", "priority"]
        for field in required_fields:
            if field not in parsed_data:
                raise ParserError(f"AI response missing required field: {field}")

        return parsed_data

    def _build_parse_result(
        self, original_text: str, parsed_data: Dict[str, Any]
    ) -> ParseResult:
        """Build ParseResult from parsed data."""
        # Normalize and validate fields
        priority = self._normalize_priority(parsed_data.get("priority", "medium"))
        task_type = self._normalize_task_type(parsed_data.get("task_type", "task"))

        # Handle estimate
        estimate = parsed_data.get("estimate")
        if estimate is not None:
            try:
                estimate = int(estimate)
                estimate = max(1, min(estimate, 21))  # Reasonable story point bounds
            except (ValueError, TypeError):
                estimate = None

        # Handle tags
        tags = parsed_data.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        # Handle confidence score
        confidence_score = parsed_data.get("confidence_score", 0.0)
        try:
            confidence_score = float(confidence_score)
            confidence_score = max(0.0, min(confidence_score, 1.0))
        except (ValueError, TypeError):
            confidence_score = 0.0

        return ParseResult(
            title=parsed_data["title"][:100],  # Limit title length
            description=parsed_data["description"],
            priority=priority,
            estimate=estimate,
            due_date=parsed_data.get("due_date"),
            task_type=task_type,
            tags=tags,
            confidence_score=confidence_score,
            raw_text=original_text,
        )
