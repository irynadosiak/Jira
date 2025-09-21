import logging
import re
from typing import List, Optional

from .base import ParseResult, TaskParser

logger = logging.getLogger(__name__)


class MockTaskParser(TaskParser):
    """Mock implementation of task text parser for testing and development."""

    def _setup(self) -> None:
        """Setup mock parser."""
        logger.info("Mock task parser initialized - no external API calls")

    def parse_text(self, text: str) -> ParseResult:
        """Parse natural language text using simple pattern matching."""
        self._validate_text(text)

        logger.info(f"Parsing task text with mock parser: {text[:100]}...")

        # Extract title (first sentence or up to 100 chars)
        title = self._extract_title(text)

        # Extract priority
        priority = self._extract_priority(text)

        # Extract estimate
        estimate = self._extract_estimate(text)

        # Extract task type
        task_type = self._extract_task_type(text)

        # Extract due date
        due_date = self._extract_due_date(text)

        # Extract tags
        tags = self._extract_tags(text)

        # Generate description
        description = self._generate_description(text, title)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(text)

        result = ParseResult(
            title=title,
            description=description,
            priority=priority,
            estimate=estimate,
            due_date=due_date,
            task_type=task_type,
            tags=tags,
            confidence_score=confidence_score,
            raw_text=text,
        )

        logger.info(
            f"Mock parsed task: '{result.title}' (confidence: {result.confidence_score:.2f})"
        )

        return result

    def _get_system_prompt(self) -> str:
        """Get mock system prompt."""
        return "Mock system prompt for development and testing purposes."

    def _extract_title(self, text: str) -> str:
        """Extract title from text."""
        # Get first sentence or first 100 characters
        sentences = re.split(r"[.!?]", text.strip())
        first_sentence = sentences[0].strip()

        if len(first_sentence) > 100:
            title = first_sentence[:97] + "..."
        else:
            title = first_sentence

        # Clean up the title
        title = re.sub(r"\s+", " ", title)  # Normalize whitespace
        title = title.strip()

        return title or "New Task"

    def _extract_priority(self, text: str) -> str:
        """Extract priority from text using keyword matching."""
        text_lower = text.lower()

        # High priority keywords
        if any(
            word in text_lower
            for word in ["urgent", "critical", "asap", "emergency", "blocker"]
        ):
            return "urgent"

        # High priority keywords
        if any(word in text_lower for word in ["high priority", "important", "major"]):
            return "high"

        # Low priority keywords
        if any(
            word in text_lower
            for word in ["low priority", "minor", "trivial", "when time permits"]
        ):
            return "low"

        return "medium"

    def _extract_estimate(self, text: str) -> Optional[int]:
        """Extract time estimate and convert to story points."""
        text_lower = text.lower()

        # Look for hour patterns
        hour_patterns = [
            r"(\d+)\s*hours?",
            r"(\d+)\s*hrs?",
            r"(\d+)\s*h\b",
        ]

        for pattern in hour_patterns:
            match = re.search(pattern, text_lower)
            if match:
                hours = int(match.group(1))
                # Convert hours to story points (rough estimate)
                if hours <= 2:
                    return 1
                elif hours <= 6:
                    return 2
                elif hours <= 16:
                    return 3
                elif hours <= 40:
                    return 5
                else:
                    return 8

        # Look for day patterns
        day_patterns = [
            r"(\d+)\s*days?",
            r"(\d+)\s*d\b",
        ]

        for pattern in day_patterns:
            match = re.search(pattern, text_lower)
            if match:
                days = int(match.group(1))
                return min(days * 3, 21)  # Max 21 story points

        # Look for story point patterns
        sp_patterns = [
            r"(\d+)\s*story points?",
            r"(\d+)\s*points?",
            r"(\d+)\s*sp\b",
        ]

        for pattern in sp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return min(int(match.group(1)), 21)

        return None

    def _extract_task_type(self, text: str) -> str:
        """Extract task type from text."""
        text_lower = text.lower()

        # Bug keywords
        if any(
            word in text_lower
            for word in ["bug", "issue", "error", "broken", "fix", "defect"]
        ):
            return "bug"

        # Feature keywords
        if any(
            word in text_lower
            for word in ["feature", "add", "new", "implement", "create", "build"]
        ):
            return "feature"

        # Story keywords
        if any(word in text_lower for word in ["user story", "story", "as a user"]):
            return "story"

        return "task"

    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date from text (basic patterns)."""
        # Look for date patterns - this is a simplified implementation
        date_patterns = [
            r"due\s+(\d{4}-\d{2}-\d{2})",
            r"by\s+(\d{4}-\d{2}-\d{2})",
            r"deadline\s+(\d{4}-\d{2}-\d{2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)

        return None

    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text."""
        tags = []

        # Look for hashtags
        hashtag_matches = re.findall(r"#(\w+)", text)
        tags.extend(hashtag_matches)

        # Look for common keywords that could be tags
        text_lower = text.lower()
        keyword_tags = []

        if "frontend" in text_lower or "ui" in text_lower:
            keyword_tags.append("frontend")
        if "backend" in text_lower or "api" in text_lower:
            keyword_tags.append("backend")
        if "database" in text_lower or "db" in text_lower:
            keyword_tags.append("database")
        if "security" in text_lower:
            keyword_tags.append("security")
        if "performance" in text_lower:
            keyword_tags.append("performance")

        tags.extend(keyword_tags)

        # Remove duplicates and limit
        return list(set(tags))[:5]

    def _generate_description(self, text: str, title: str) -> str:
        """Generate description from text."""
        # If text is the same as title, create a more detailed description
        if text.strip() == title.strip() or len(text) <= len(title) + 10:
            return f"Task to {text.lower()}"

        # If text is short, but different from title, use it as description
        if len(text) <= 200:
            # Remove the title part if it's at the beginning of the text
            description = text
            if text.lower().startswith(title.lower()):
                remaining = text[len(title) :].strip()
                if remaining and remaining.startswith((".", ",", ":", ";")):
                    remaining = remaining[1:].strip()
                description = remaining if remaining else f"Task to {title.lower()}"
            return description

        # For longer text, create a structured description
        description_parts = [
            "Details:",
            text,
        ]

        return "\n".join(description_parts)

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score based on text characteristics."""
        confidence = 0.5  # Base confidence

        # Length bonus
        if 20 <= len(text) <= 500:
            confidence += 0.2

        # Structure bonus (has punctuation)
        if any(char in text for char in ".!?"):
            confidence += 0.1

        # Keyword bonus (has action words)
        action_words = [
            "fix",
            "add",
            "create",
            "implement",
            "update",
            "remove",
            "build",
        ]
        if any(word in text.lower() for word in action_words):
            confidence += 0.1

        # Priority mention bonus
        if any(word in text.lower() for word in ["urgent", "high", "low", "priority"]):
            confidence += 0.1

        return min(confidence, 1.0)
