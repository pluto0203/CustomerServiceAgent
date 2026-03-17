from celery import Celery

celery_app = Celery("agent")

# Values are expected to be loaded from environment variables later.
celery_app.conf.broker_url = "redis://redis:6379/0"
celery_app.conf.result_backend = "redis://redis:6379/1"
