import logging

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User
from django.db.models import Prefetch

from .models import Task, TaskActivity, TaskSummary
from .services import EstimationError, TaskEstimationService, TaskSummaryService

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class TaskActivitySerializer(serializers.ModelSerializer):
    """Simple activity serializer."""

    class Meta:
        model = TaskActivity
        fields = "__all__"


class TaskSummarySerializer(serializers.ModelSerializer):
    """Serializer for TaskSummary model."""

    class Meta:
        model = TaskSummary
        fields = [
            "summary_text",
            "created_at",
            "updated_at",
            "token_usage",
            "last_activity_processed",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "token_usage",
            "last_activity_processed",
        ]


class TaskSerializer(serializers.ModelSerializer):
    """Task serializer with related data."""

    assignee = UserSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="assignee",
        write_only=True,
        required=False,
        allow_null=True,
    )
    reporter_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="reporter", write_only=True, required=False
    )
    activities = TaskActivitySerializer(many=True, read_only=True)
    ai_summary = TaskSummarySerializer(read_only=True, required=False)

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        return super().create(validated_data)


class TaskFilter(django_filters.FilterSet):
    """Comprehensive filtering for tasks."""

    assignee = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), empty_label="All Assignees"
    )
    reporter = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(), empty_label="All Reporters"
    )
    unassigned = django_filters.BooleanFilter(
        field_name="assignee", lookup_expr="isnull", label="Unassigned tasks"
    )

    class Meta:
        model = Task
        fields = {
            "status": ["exact"],
            "priority": ["exact"],
            "assignee": ["exact"],
            "reporter": ["exact"],
            "estimate": ["exact", "gte", "lte"],
            "created_at": ["date", "date__gte", "date__lte"],
            "due_date": ["date", "date__gte", "date__lte", "isnull"],
        }


class TaskListCreateView(generics.ListCreateAPIView):
    """List and create tasks with filtering and search."""

    queryset = Task.objects.select_related("reporter", "assignee").all()
    serializer_class = TaskSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TaskFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority", "status", "due_date"]
    ordering = ["-created_at"]


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, delete tasks."""

    serializer_class = TaskSerializer

    def get_queryset(self):
        # Limit activities to last 10 by default, configurable via query param
        activity_limit = int(self.request.query_params.get("activity_limit", 10))

        # Create prefetch for recent activities only
        recent_activities = TaskActivity.objects.order_by("-timestamp")[:activity_limit]

        return Task.objects.select_related("reporter", "assignee").prefetch_related(
            Prefetch("activities", queryset=recent_activities), "ai_summary"
        )


class TaskSummaryView(APIView):
    """Get existing summary for a task."""

    def get(self, request, pk):
        """Get existing summary for the task."""
        try:
            task = Task.objects.get(pk=pk)
            summary = getattr(task, "ai_summary", None)

            if summary:
                serializer = TaskSummarySerializer(summary)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "No summary available for this task"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve summary: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        """Delete existing summary for the task."""
        try:
            task = Task.objects.get(pk=pk)
            summary_service = TaskSummaryService()
            deleted = summary_service.delete_summary(task.id)

            if deleted:
                return Response(
                    {"message": "Summary deleted successfully"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "No summary found to delete"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete summary: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskSummaryGenerateView(APIView):
    """Generate or update AI summary for a task."""

    def post(self, request, pk):
        """Generate or update AI summary for the task."""
        try:
            task = Task.objects.get(pk=pk)
            summary_service = TaskSummaryService()
            summary = summary_service.create_or_update_summary(task.id)

            serializer = TaskSummarySerializer(summary)
            return Response(
                {
                    "message": "Summary generated successfully",
                    "summary": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate summary: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TaskActivityListView(generics.ListAPIView):
    """List activities for a specific task."""

    serializer_class = TaskActivitySerializer

    def get_queryset(self):
        task_id = self.kwargs["task_id"]
        return TaskActivity.objects.filter(task_id=task_id)


class UserListView(generics.ListAPIView):
    """List users for assignment."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


class TaskEstimationView(APIView):
    """API view for getting AI-powered task estimations."""

    def get(self, request, pk):
        """Get AI estimation for a task."""
        try:
            # Create estimation service
            estimation_service = TaskEstimationService()

            # Check if task can be estimated
            if not estimation_service.can_estimate(pk):
                return Response(
                    {
                        "error": "Task cannot be estimated",
                        "detail": "Task must have both title and description for accurate estimation",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get estimation
            result = estimation_service.estimate_task(pk)

            return Response(
                {
                    "task_id": pk,
                    "estimated_hours": result.estimated_hours,
                    "confidence_score": result.confidence_score,
                    "reasoning": result.reasoning,
                    "similar_tasks": result.similar_tasks,
                    "metadata": result.metadata,
                }
            )

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except EstimationError as e:
            logger.error(f"Estimation error for task {pk}: {str(e)}")
            return Response(
                {"error": "Estimation failed", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Failed to estimate task {pk}: {str(e)}")
            return Response(
                {"error": "Failed to estimate task"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
