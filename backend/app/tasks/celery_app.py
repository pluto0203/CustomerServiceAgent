from celery import Celery

from app.core.config import settings

celery_app = Celery(
	"agent",
	include=["app.tasks.process_a2a_message"],
)

celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True
celery_app.conf.timezone = "UTC"
