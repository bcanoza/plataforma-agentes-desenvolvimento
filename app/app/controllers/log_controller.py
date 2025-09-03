from fastapi import APIRouter, Body
import logging

router = APIRouter(prefix="/logs", tags=["logs"])
logger = logging.getLogger("assistente")

@router.post("")
def write_log(message: str = Body(...)):
    logger.info(f"[log_controller] {message}")
    return {"logged": True, "message": message}
