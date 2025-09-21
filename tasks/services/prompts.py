import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Task, TaskActivity

logger = logging.getLogger(__name__)


class PromptBuilderInterface(ABC):
    """Abstract interface for prompt builders."""

    @abstractmethod
    def build(self) -> str:
        """Build the final prompt."""
        pass


class EstimationPromptBuilder(PromptBuilderInterface):
    """Builder for AI estimation prompts."""

    def __init__(self, task: Task):
        """Initialize with task."""
        self.task = task
        self.similar_tasks: List[Dict[str, Any]] = []
        self.instructions: List[str] = []
        self.analysis_factors: List[str] = []

    def add_similar_tasks(
        self, similar_tasks: List[Dict[str, Any]]
    ) -> "EstimationPromptBuilder":
        """Add similar tasks context."""
        self.similar_tasks = similar_tasks
        return self

    def add_analysis_factor(self, factor: str) -> "EstimationPromptBuilder":
        """Add analysis factor."""
        self.analysis_factors.append(factor)
        return self

    def add_instruction(self, instruction: str) -> "EstimationPromptBuilder":
        """Add custom instruction."""
        self.instructions.append(instruction)
        return self

    def _build_similar_tasks_section(self) -> List[str]:
        """Build similar tasks section."""
        if not self.similar_tasks:
            return ["No historical similar tasks available."]

        lines = ["HISTORICAL SIMILAR TASKS:"]
        for i, task in enumerate(self.similar_tasks, 1):
            description = task.get("description", "")
            if len(description) > 150:
                description = description[:150] + "..."

            lines.extend(
                [
                    f"{i}. Title: {task['title']}",
                    f"   Description: {description}",
                    f"   Priority: {task['priority']}",
                    f"   Actual Effort: {task['estimate']} hours",
                    "",
                ]
            )

        return lines

    def _build_task_section(self) -> List[str]:
        """Build new task section."""
        assignee = self.task.assignee.username if self.task.assignee else "Unassigned"

        return [
            "NEW TASK TO ESTIMATE:",
            f"Title: {self.task.title}",
            f"Description: {self.task.description}",
            f"Priority: {self.task.priority}",
            f"Assignee: {assignee}",
            "",
        ]

    def _build_analysis_section(self) -> List[str]:
        """Build analysis instructions section."""
        default_factors = [
            "Task complexity and technical requirements",
            "Similar functionality or features",
            "Priority level and urgency",
            "Scope and deliverables",
            "Potential risks and unknowns",
        ]

        factors = self.analysis_factors if self.analysis_factors else default_factors

        lines = [
            "ANALYSIS INSTRUCTIONS:",
            "1. Analyze the new task's complexity, scope, and requirements",
            "2. Compare it with the historical tasks to find patterns and similarities",
            "3. Consider factors like:",
        ]

        for factor in factors:
            lines.append(f"   - {factor}")

        lines.append("")
        return lines

    def _build_format_section(self) -> List[str]:
        """Build response format section."""
        return [
            "Please provide your estimation in the following JSON format:",
            "{",
            '    "estimated_hours": <number>,',
            '    "confidence_score": <number between 0 and 1>,',
            '    "reasoning": "<detailed explanation of your estimation process>",',
            '    "similar_task_analysis": [',
            "        {",
            '            "task_id": <id>,',
            '            "similarity_score": <number between 0 and 1>,',
            '            "similarity_factors": ["<factor1>", "<factor2>"]',
            "        }",
            "    ],",
            '    "risk_factors": ["<factor1>", "<factor2>"],',
            '    "assumptions": ["<assumption1>", "<assumption2>"]',
            "}",
            "",
            "Be thorough in your analysis and provide a realistic estimate. "
            "The confidence score should reflect how certain you are based on "
            "the available similar tasks and task clarity.",
        ]

    def build(self) -> str:
        """Build the complete estimation prompt."""
        sections = [
            [
                "You are an expert software project manager specializing in task estimation.",
                "Your job is to estimate the effort required for a new task by analyzing its similarity to historical tasks.",
                "",
            ],
            self._build_similar_tasks_section(),
            [""],
            self._build_task_section(),
            self._build_analysis_section(),
        ]

        # Add custom instructions if any
        if self.instructions:
            sections.append(["ADDITIONAL INSTRUCTIONS:"] + self.instructions + [""])

        sections.append(self._build_format_section())

        # Flatten all sections
        all_lines = []
        for section in sections:
            all_lines.extend(section)

        return "\n".join(all_lines)


class SummaryPromptBuilder(PromptBuilderInterface):
    """Builder for AI summary prompts."""

    def __init__(self, task: Task):
        """Initialize with task."""
        self.task = task
        self.activities: List[TaskActivity] = []
        self.previous_summary: Optional[str] = None
        self.focus_areas: List[str] = []

    def add_activities(self, activities: List[TaskActivity]) -> "SummaryPromptBuilder":
        """Add activities to summarize."""
        self.activities = activities
        return self

    def set_previous_summary(self, summary: str) -> "SummaryPromptBuilder":
        """Set previous summary for updates."""
        self.previous_summary = summary
        return self

    def add_focus_area(self, area: str) -> "SummaryPromptBuilder":
        """Add focus area for summary."""
        self.focus_areas.append(area)
        return self

    def _build_context_section(self) -> List[str]:
        """Build task context section."""
        lines = [
            f"Task: {self.task.title}",
            f"Description: {self.task.description or 'No description provided'}",
            f"Current Status: {self.task.get_status_display()}",
            f"Priority: {self.task.get_priority_display()}",
        ]

        # Add assignee and reporter info
        if self.task.assignee:
            lines.append(f"Assignee: {self.task.assignee.username}")
        if self.task.reporter:
            lines.append(f"Reporter: {self.task.reporter.username}")

        # Add estimate if available
        if self.task.estimate:
            lines.append(f"Estimate: {self.task.estimate} story points")

        # Add due date if available
        if self.task.due_date:
            lines.append(f"Due Date: {self.task.due_date.strftime('%Y-%m-%d')}")

        lines.append("")
        return lines

    def _build_previous_summary_section(self) -> List[str]:
        """Build previous summary section."""
        if not self.previous_summary:
            return []

        return [
            "PREVIOUS SUMMARY:",
            self.previous_summary,
            "",
            "NEW ACTIVITIES TO INCORPORATE:",
            "",
        ]

    def _build_activities_section(self) -> List[str]:
        """Build activities section."""
        if not self.activities:
            return ["No recent activities to summarize."]

        lines = ["RECENT ACTIVITIES:"]
        for activity in self.activities:
            timestamp = activity.timestamp.strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {timestamp}: {activity.description}")

        lines.append("")
        return lines

    def _build_instructions_section(self) -> List[str]:
        """Build instructions section."""
        base_instructions = [
            "Please provide a concise but comprehensive summary of the task's current state.",
            "Focus on:",
            "- Current progress and status",
            "- Key activities and changes",
            "- Important decisions or blockers",
            "- Overall trajectory and next steps",
        ]

        if self.focus_areas:
            base_instructions.extend(["", "Additionally, pay special attention to:"])
            for area in self.focus_areas:
                base_instructions.append(f"- {area}")

        if self.previous_summary:
            base_instructions.extend(
                [
                    "",
                    "Update the previous summary with the new activities, maintaining continuity while highlighting recent changes.",
                ]
            )

        return base_instructions

    def build(self) -> str:
        """Build the complete summary prompt."""
        sections = [
            self._build_context_section(),
            self._build_previous_summary_section(),
            self._build_activities_section(),
            self._build_instructions_section(),
        ]

        # Flatten all sections
        all_lines = []
        for section in sections:
            all_lines.extend(section)

        return "\n".join(all_lines)


class SystemPromptBuilder:
    """Builder for system prompts."""

    def __init__(self, role: str):
        """Initialize with role."""
        self.role = role
        self.capabilities: List[str] = []
        self.constraints: List[str] = []
        self.response_format: Optional[str] = None

    def add_capability(self, capability: str) -> "SystemPromptBuilder":
        """Add capability description."""
        self.capabilities.append(capability)
        return self

    def add_constraint(self, constraint: str) -> "SystemPromptBuilder":
        """Add constraint."""
        self.constraints.append(constraint)
        return self

    def set_response_format(self, format_desc: str) -> "SystemPromptBuilder":
        """Set response format requirement."""
        self.response_format = format_desc
        return self

    def build(self) -> str:
        """Build system prompt."""
        parts = [f"You are {self.role}."]

        if self.capabilities:
            parts.append(
                " ".join([f"You excel at {cap}." for cap in self.capabilities])
            )

        if self.constraints:
            parts.extend(self.constraints)

        if self.response_format:
            parts.append(self.response_format)

        return " ".join(parts)


# Factory for creating prompt builders
class PromptBuilderFactory:
    """Factory for creating prompt builders."""

    @staticmethod
    def create_estimation_prompt_builder(task: Task) -> EstimationPromptBuilder:
        """Create estimation prompt builder."""
        return EstimationPromptBuilder(task)

    @staticmethod
    def create_summary_prompt_builder(task: Task) -> SummaryPromptBuilder:
        """Create summary prompt builder."""
        return SummaryPromptBuilder(task)

    @staticmethod
    def create_system_prompt_builder(role: str) -> SystemPromptBuilder:
        """Create system prompt builder."""
        return SystemPromptBuilder(role)
