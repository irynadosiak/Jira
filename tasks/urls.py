from django.urls import path

from . import api, views

app_name = "tasks"

urlpatterns = [
    # Web interface
    path("", views.task_list, name="task-list"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("create/", views.task_create, name="task-create"),
    path("<int:pk>/", views.task_detail, name="task-detail"),
    path("<int:pk>/edit/", views.task_update, name="task-update"),
    path("<int:pk>/delete/", views.task_delete, name="task-delete"),
    path("<int:pk>/quick-update/", views.task_quick_update, name="task-quick-update"),
    # API endpoints
    path("api/", api.TaskListCreateView.as_view(), name="api-task-list-create"),
    path("api/<int:pk>/", api.TaskDetailView.as_view(), name="api-task-detail"),
    path(
        "api/<int:task_id>/activities/",
        api.TaskActivityListView.as_view(),
        name="api-task-activities",
    ),
    # AI Summary endpoints
    path(
        "api/<int:pk>/summary/", api.TaskSummaryView.as_view(), name="api-task-summary"
    ),
    path(
        "api/<int:pk>/generate-summary/",
        api.TaskSummaryGenerateView.as_view(),
        name="api-task-generate-summary",
    ),
    path("api/users/", api.UserListView.as_view(), name="api-users"),
]
