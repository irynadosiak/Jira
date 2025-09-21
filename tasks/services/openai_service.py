import logging
from typing import List, Optional

from openai import OpenAI

from ..models import Task, TaskActivity
from .base import AIConfigurationError, AIProvider, AIServiceError, AISummaryResult

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI implementation of AI provider."""

    def _setup(self) -> None:
        """Setup OpenAI client."""
        if not self.config.api_key:
            raise AIConfigurationError("OpenAI API key is required")

        try:
            self.client = OpenAI(api_key=self.config.api_key)
            logger.info("OpenAI provider initialized successfully")
        except Exception as e:
            raise AIConfigurationError(f"Failed to initialize OpenAI client: {str(e)}")

    def generate_task_summary(
        self,
        task: Task,
        new_activities: List[TaskActivity],
        previous_summary: Optional[str] = None,
    ) -> AISummaryResult:
        """Generate or update task summary using OpenAI."""
        try:
            context = self._build_context(task, new_activities, previous_summary)

            logger.info(
                f"Generating summary for task {task.id} with {len(new_activities)} activities"
            )

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": context},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            summary_text = response.choices[0].message.content
            if summary_text is None:
                raise Exception("OpenAI returned empty response")
            summary_text = summary_text.strip()

            usage = response.usage
            tokens_used = usage.total_tokens if usage else 0

            logger.info(
                f"Successfully generated summary for task {task.id}, used {tokens_used} tokens"
            )

            return AISummaryResult(summary=summary_text, tokens_used=tokens_used)

        except Exception as e:
            logger.error(f"Failed to generate summary for task {task.id}: {str(e)}")
            raise AIServiceError(f"OpenAI API error: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for OpenAI."""
        return (
            "You are a project management assistant that creates concise, professional "
            "summaries of task activities. Your summaries should:\n"
            "- Be clear and easy to understand\n"
            "- Highlight key changes and progress\n"
            "- Include relevant dates when significant\n"
            "The output should be no more than 100 symbols."
        )
