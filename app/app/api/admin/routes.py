# app/api/admin/routes.py
"""
Controller administrativo - Utilitários, diagnósticos, reload.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.api.auth.dependencies import verify_api_key, require_admin, CurrentUser
from app.core.controller_loader import reload_controllers
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/ping")
async def admin_ping(current: CurrentUser = Depends(require_admin)):
    """Ping administrativo com informações do admin."""
    return {
        "ok": True,
        "adminId": current["sub"],
        "roles": current["roles"],
    }


@router.get("/routes")
def admin_list_routes() -> Dict[str, Any]:
    """Lista todas as rotas registradas na aplicação."""
    from fastapi import FastAPI
    from app.main import app
    
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            route_info = {
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', None),
            }
            routes.append(route_info)
    
    return {"count": len(routes), "routes": routes}


@router.get("/controllers")
def admin_list_controllers() -> Dict[str, Any]:
    """Lista controllers já carregados."""
    from app.core.controller_loader import _loaded_modules
    
    loaded = list(_loaded_modules)
    return {"count": len(loaded), "modules": loaded}


@router.post("/reload")
def admin_reload_controllers(
    full: bool = Query(
        True,
        description=(
            "Se True, limpa cache de módulos antes de importar (garante código novo). "
            "Se False, faz reload 'suave'. Em ambos os casos há RESCAN do diretório."
        )
    )
) -> Dict[str, Any]:
    """
    Recarrega controllers com rescan do diretório.
    
    - full=False → reload "suave" (mantém sys.modules, evita duplicidade)
    - full=True  → *limpa* sys.modules dos controllers + *zera* _loaded_modules,
                   então rescaneia e inclui novamente os routers.
    """
    from app.main import app
    
    try:
        loaded = reload_controllers(app, full=full)
        return {
            "ok": True,
            "full": full,
            "loaded_count": len(loaded),
            "loaded_modules": loaded,
        }
    except Exception as e:
        logger.exception("admin.reload.error")
        return {
            "ok": False,
            "error": str(e),
            "full": full,
        }



