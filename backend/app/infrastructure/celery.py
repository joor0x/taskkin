from celery import Celery

from app.config import settings

celery_app = Celery(
    "taskkin",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Autodiscover tasks from app.webhooks, app.tasks, etc.
celery_app.autodiscover_tasks(["app.webhooks", "app.tasks"])

# Configure Celery Beat periodic schedules
celery_app.conf.beat_schedule = {
    "check-expired-tasks-every-5-minutes": {
        "task": "app.tasks.tasks.check_expired_tasks",
        "schedule": 300.0,  # Run every 5 minutes
    },
}
