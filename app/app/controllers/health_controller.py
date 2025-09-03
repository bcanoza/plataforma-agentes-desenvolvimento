from fastapi import APIRouter
import logging

router = APIRouter(prefix="/healthz", tags=["health"])
logger = logging.getLogger("assistente")

@router.get("")
def healthz_root():
    return {"status": "ok"}

@router.get("/deep")
def healthz_deep():
    return {"status": "ok", "checks": {"api": "ok"}}
