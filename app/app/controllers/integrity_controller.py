import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.controllers.auth_controller import verify_api_key
from app.core.logging_config import get_logger
# Diagnóstico fica em app/services/diagnostics_service.py (plural: services)
from app.services.diagnostics_service import DiagnosticsService

logger = get_logger("assistente")
router = APIRouter(prefix="/integrity", tags=["Integrity"])


class PathsModel(BaseModel):
    paths: List[str]


@router.post("/check")
def check_paths(payload: PathsModel, _: bool = Depends(verify_api_key)):
    """
    Verifica múltiplos caminhos: existência e sintaxe Python (quando aplicável).
    """
    try:
        svc = DiagnosticService()
        results = svc.run_all(payload.paths)
        ok = True
        for r in results:
            if (r.get("exists") is False) or (r.get("syntax_ok") is False):
                ok = False
        return {"ok": ok, "results": results}
    except Exception as e:
        logger.exception("[integrity_controller] erro no check")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-file")
def check_file(path: str = Query(...), _: bool = Depends(verify_api_key)):
    """
    Verifica um único arquivo/caminho: existência e sintaxe Python (quando aplicável).
    """
    try:
        svc = DiagnosticService()
        results = svc.run_all([path])
        ok = True
        for r in results:
            if (r.get("exists") is False) or (r.get("syntax_ok") is False):
                ok = False
        return {"ok": ok, "results": results}
    except Exception as e:
        logger.exception("[integrity_controller] erro no check-file")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
