from __future__ import annotations
from fastapi import APIRouter, Depends, Body
from app.controllers.auth_controller import verify_api_key
from app.services.diagnostics_service import DiagnosticsService
try:
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    from app.config import settings
    logger = logging.getLogger(getattr(settings, "LOGGER_NAME", "assistente"))

router = APIRouter(prefix="/admin/diagnostics", tags=["Admin", "Diagnostics"])

@router.post("/code")
def run_code_checks(
    payload: dict = Body(default={}),
    authorized: bool = Depends(verify_api_key),
):
    paths  = payload.get("paths")  or ["app/main.py", "app/controllers/auth_controller.py"]
    checks = payload.get("checks") or None  # lista opcional; pode incluir 'ruff' e 'black'
    opts   = payload.get("options") or {}

    service = DiagnosticsService()
    results = service.run_all(paths, checks=checks, **opts)

    # Sinalização geral de OK: nenhum exists=False / syntax_ok=False / inside_root=False / size_ok=False / encoding_utf8=False
    ok = True
    for r in results:
        if (
            r.get("exists") is False or
            r.get("syntax_ok") is False or
            r.get("inside_root") is False or
            r.get("size_ok") is False or
            r.get("encoding_utf8") is False
        ):
            ok = False
            break

    return {"ok": ok, "checked": paths, "checks": checks, "results": results}

__all__ = ["router"]
