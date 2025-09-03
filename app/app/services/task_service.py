import logging
"""Serviço de manipulação de tarefas."""
from app.core.celery_app import celery_app

def dispatch_task(task_name: str, args: list):
    return celery_app.send_task(task_name, args=args)
