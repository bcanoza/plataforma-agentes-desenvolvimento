# app/controllers/admin_controller.py
"""
Admin Controller
----------------
Utilidades administrativas da API. Todas as rotas exigem autenticação via
header `x_api_key` (validação feita por `verify_api_key`).

Endpoints principais:
- GET  /admin/ping                     → ping simples (auth + disponibilidade)
- GET  /admin/routes                   → lista as rotas registradas na aplicação
- GET  /admin/controllers              → lista controllers já carregados
- POST /admin/reload		       → rescan + (opcional) limpeza de cache de módulos

Notas:
- O recarregamento de controllers utiliza `reload_controllers(full=...)`, que
  realiza um *rescan* do diretório `app/controllers` e inclui novos arquivos
  `*_controller.py` que exportem um objeto `router` (APIRouter). Com `full=True`,
  o cache de módulos é limpo antes de importar (garantindo código novo em disco).
- O loader é idempotente: routers já incluídos não são adicionados novamente.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.controllers.auth_controller import verify_api_key
from app.core.controller_loader import reload_controllers
from app.core.logging_config import get_logger

from app.security.jwt_dependency import require_admin, CurrentUser


logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_api_key)],
)

@router.get("/ping")
async def admin_ping(current: CurrentUser = Depends(require_admin)):
    return {
        "ok": True,
        "adminId": current["sub"],
        "roles": current["roles"],
    }

@router.get("/routes")
def admin_list_routes() -> Dict[str, Any]:
    """
    Lista as rotas registradas na aplicação (métodos, path, nome e módulo).
    Útil para diagnosticar se novos controllers/rotas foram carregados.
    """
    # Importa a instância viva do FastAPI somente dentro da função
    from app.main import app
    from fastapi.routing import APIRoute

    items: List[Dict[str, Any]] = []
    for r in app.router.routes:
        if isinstance(r, APIRoute):
            try:
                endpoint = r.endpoint
                qualname = getattr(endpoint, "__qualname__", None) or endpoint.__class__.__name__
                module = getattr(endpoint, "__module__", None) or "unknown"
            except Exception:
                qualname, module = "unknown", "unknown"

            items.append({
                "path": r.path,
                "methods": sorted(list(r.methods or [])),
                "name": r.name,
                "endpoint": qualname,
                "module": module,
            })

    # Ordena por path para facilitar leitura
    items.sort(key=lambda x: x["path"])
    return {"count": len(items), "routes": items}


@router.get("/controllers")
def admin_list_controllers() -> Dict[str, Any]:
    """
    Lista os controllers já carregados pelo auto-discovery.
    Observação: acessa o registro interno do loader se disponível.
    """
    loaded: List[str] = []
    try:
        # Import tardio para evitar ciclos
        import app.core.controller_loader as cl
        # Acessa o set interno somente para fins de diagnóstico
        loaded = sorted(list(getattr(cl, "_loaded_modules", set())))
    except Exception as e:
        logger.warning("[admin.controllers] não foi possível ler _loaded_modules: %s", e)
    return {"count": len(loaded), "modules": loaded}


@router.post("/reload")
def admin_reload_controllers(
    full: bool = Query(
        True,
        description=(
            "Se True, limpa cache de módulos antes de importar (garante código novo). "
            "Se False, faz reload 'suave'. Em ambos os casos há RESCAN do diretório."
        ),
    )
) -> Dict[str, Any]:
    """
    Recarrega controllers com RESCAN do diretório `app/controllers`.
    - `full=True`: limpa sys.modules dos controllers antes de importar.
    - `full=False`: reload suave (mantém cache), ainda assim faz rescan.

    Retorna a lista de módulos *novos* incluídos nesta chamada.
    """
    from app.main import app  # evita import cíclico no topo do módulo
    loaded_now = reload_controllers(app, full=full)
    mode = "full" if full else "soft"
    logger.info("[admin.reload.controllers] mode=%s loaded_now=%s", mode, loaded_now)
    return {"mode": mode, "reloaded": loaded_now}
