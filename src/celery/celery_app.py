from celery import Celery

from src.config.config import CELERY_BROKER_URL, CELERY_BACKEND


celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BACKEND,
    include=["src.celery.worker"],
)

celery_app.conf.task_routes = {"src.worker.*": {"queue": "default"}}
