from django.urls import re_path

from .ai_consumers import (
    TaskCreateConsumer,
    TaskEstimationConsumer,
    TaskParseConsumer,
    TaskSummaryConsumer,
)

websocket_urlpatterns = [
    re_path(
        r"ws/tasks/(?P<task_id>\d+)/estimation/$",
        TaskEstimationConsumer.as_asgi(),
        name="ws_task_estimation",
    ),
    re_path(
        r"ws/tasks/(?P<task_id>\d+)/summary/$",
        TaskSummaryConsumer.as_asgi(),
        name="ws_task_summary",
    ),
    re_path(r"ws/tasks/parse/$", TaskParseConsumer.as_asgi(), name="ws_task_parse"),
    re_path(r"ws/tasks/create/$", TaskCreateConsumer.as_asgi(), name="ws_task_create"),
]
