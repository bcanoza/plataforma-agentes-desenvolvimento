import logging
from fastapi import APIRouter, Body
from celery.result import AsyncResult
from app.core.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/dispatch")
def dispatch_task(task: str = Body(...), args: list = Body(default=[])):
    job = celery_app.send_task(task, args=args)
    return {"queued": True, "task_id": job.id}

@router.get("/{task_id}")
def task_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    out = {"task_id": task_id, "status": res.status}
    if res.status == "SUCCESS":
        out["result"] = res.result
    elif res.status == "FAILURE":
        out["error"] = str(res.result)
    return out
