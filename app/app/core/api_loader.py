# app/core/api_loader.py
"""
Loader para nova arquitetura de API organizada por domínio.
Substitui o controller_loader.py para a nova estrutura app/api/
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
import logging
from typing import List

from fastapi import FastAPI
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_API_PACKAGE: str = getattr(settings, "API_PACKAGE", "app.api")
ROUTES_MODULE: str = "routes"

# Registro interno de módulos já incluídos
_loaded_modules: set[str] = set()


def _iter_api_modules(package_name: str) -> List[str]:
    """Rescaneia o pacote e retorna módulos que têm routes.py."""
    importlib.invalidate_caches()
    pkg = importlib.import_module(package_name)
    modules: List[str] = []

    for m in pkgutil.iter_modules(pkg.__path__, prefix=package_name + "."):
        try:
            spec = importlib.util.find_spec(m.name)
            if not spec or not getattr(spec, "origin", None):
                continue
            origin = spec.origin
            
            # Verifica se é um diretório com routes.py
            if origin.endswith("__init__.py"):
                # Tenta importar o módulo routes
                routes_module_name = f"{m.name}.{ROUTES_MODULE}"
                routes_spec = importlib.util.find_spec(routes_module_name)
                if routes_spec and routes_spec.origin:
                    modules.append(routes_module_name)
                    
        except Exception as e:
            logger.warning("[api_loader] falha inspecionando %s: %s", m.name, e)

    modules.sort()
    return modules


def _clear_sys_modules_for(package_name: str) -> int:
    """Remove do sys.modules todos os módulos do pacote API."""
    to_del = [m for m in list(sys.modules.keys()) if m == package_name or m.startswith(package_name + ".")]
    for m in to_del:
        try:
            del sys.modules[m]
        except Exception:
            pass
    return len(to_del)


def load_api_modules(
    app: FastAPI,
    package_name: str = DEFAULT_API_PACKAGE,
    *,
    rescan: bool = True,
    clear_module_cache: bool = False,
) -> List[str]:
    """
    Carrega módulos da nova arquitetura API.
    - rescan=True  → percorre o diretório a CADA chamada
    - clear_module_cache=True → remove módulos do sys.modules antes de importar
    """
    logger.info(
        "[api_loader] load_api_modules(rescan=%s, clear_module_cache=%s, package=%s)",
        rescan, clear_module_cache, package_name
    )

    module_names = _iter_api_modules(package_name) if rescan else list(_loaded_modules)
    loaded_now: List[str] = []

    for mod_name in module_names:
        try:
            if clear_module_cache:
                if mod_name in sys.modules:
                    del sys.modules[mod_name]

            module = importlib.import_module(mod_name)

            # Reload suave quando não limpamos cache
            if not clear_module_cache and mod_name in sys.modules:
                module = importlib.reload(module)

            router = getattr(module, "router", None)
            if router is None:
                logger.debug("[api_loader] ignorando %s (sem `router`)", mod_name)
                continue

            if mod_name in _loaded_modules:
                logger.debug("[api_loader] já carregado: %s (skip include)", mod_name)
                continue

            app.include_router(router)
            _loaded_modules.add(mod_name)
            loaded_now.append(mod_name)
            logger.info("[api_loader] loaded: %s", mod_name)

        except Exception as e:
            logger.error("[api_loader] erro importando %s: %s", mod_name, e)

    if not loaded_now:
        logger.info("[api_loader] nenhum novo módulo incluído (total atual=%d)", len(_loaded_modules))
    return loaded_now


def include_api_modules(app: FastAPI) -> List[str]:
    """Startup: rescan inicial sem limpar cache (rápido)."""
    return load_api_modules(app, DEFAULT_API_PACKAGE, rescan=True, clear_module_cache=False)


def reload_api_modules(app: FastAPI, *, full: bool = True) -> List[str]:
    """
    Recarrega módulos da API com RESCAN do diretório.
    
    - full=False → reload "suave" (mantém sys.modules, evita duplicidade)
    - full=True  → *limpa* sys.modules + *zera* _loaded_modules,
                   então rescaneia e inclui novamente os routers.
    """
    if full:
        removed = _clear_sys_modules_for(DEFAULT_API_PACKAGE)
        logger.info("[api_loader] full reload: sys.modules limpos (%d módulos)", removed)
        _loaded_modules.clear()
        logger.info("[api_loader] full reload: registro interno resetado")

    return load_api_modules(app, DEFAULT_API_PACKAGE, rescan=True, clear_module_cache=full)



