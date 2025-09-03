"""Configuração do Celery."""
import os
from celery import Celery
from app.config import settings

broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

celery_app = Celery("odonto_assistente", broker=broker_url, backend=result_backend)
celery_app.conf.update(
    task_default_queue="default",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone=settings.TZ,
    enable_utc=False,
)

@celery_app.task(name="tasks.ping")
def ping(message: str = "hello"):
    return {"echo": message}
