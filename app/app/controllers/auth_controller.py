# app/controllers/auth_controller.py
from __future__ import annotations

import logging
from fastapi import APIRouter, Header, HTTPException
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

def verify_api_key(x_api_key: str = Header(..., convert_underscores=False)):
    """
    Dependency para proteger endpoints com API Key.
    Lê a chave do cabeçalho `X-API-Key` e compara com settings.APP_SECRET.
    """
    if x_api_key != settings.APP_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@router.get("/validate")
def validate_api_key(x_api_key: str = Header(..., convert_underscores=False)):
    verify_api_key(x_api_key)
    return {"valid": True}

__all__ = ["router", "verify_api_key"]