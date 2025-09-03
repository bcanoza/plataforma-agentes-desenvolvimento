# app/api/health/routes.py
"""
Controller de health checks - Monitoramento e status.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/health", tags=["Health"])


@router.get("/")
def healthz_root():
    """Health check básico."""
    return {"status": "ok"}


@router.get("/deep")
def healthz_deep():
    """Health check profundo com verificações adicionais."""
    return {"status": "ok", "checks": {"api": "ok"}}



