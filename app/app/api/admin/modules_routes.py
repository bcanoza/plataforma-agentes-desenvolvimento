# app/api/admin/modules_routes.py
"""
APIs de administração de módulos.

Permite:
- Listar módulos registrados
- Ativar/desativar módulos  
- Atualizar configuração dinâmica
- Registrar novos módulos
- Health monitoring
- Hot-reload de módulos
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from fastapi.responses import JSONResponse

from app.api.auth.dependencies import require_admin, CurrentUser
from app.core.service_container import container
from app.services.module_registry_service import ModuleRegistryService, PgModuleRepo, ModuleError
from app.core.logging_config import get_logger

logger = get_logger("admin.modules")

router = APIRouter(prefix="/v1/admin/modules", tags=["Module Administration"])

# Service instances
registry_service = ModuleRegistryService(PgModuleRepo())


# =========================
#   SCHEMAS  
# =========================
from pydantic import BaseModel, Field

class ModuleInfoResponse(BaseModel):
    """Response completo de informações do módulo."""
    id: str
    name: str
    kind: str
    version: str
    status: str
    
    displayOrder: int
    description: Optional[str]
    author: Optional[str]
    icon: Optional[str]
    
    manifest: dict
    config: dict
    
    installedAt: str
    lastLoadedAt: Optional[str]
    lastErrorAt: Optional[str]
    errorMessage: Optional[str]
    loadCount: int
    
    createdAt: str
    updatedAt: str


class RegisterModuleRequest(BaseModel):
    """Request para registrar novo módulo."""
    manifest: Dict[str, Any] = Field(..., description="Manifesto JSON do módulo")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuração inicial")


class UpdateConfigRequest(BaseModel):
    """Request para atualizar configuração."""
    config: Dict[str, Any] = Field(..., description="Nova configuração do módulo")


class ModuleActionResponse(BaseModel):
    """Response padrão para ações em módulos."""
    success: bool
    message: str
    moduleId: str


class ModuleStatsResponse(BaseModel):
    """Estatísticas do sistema de módulos."""
    totalModules: int
    activeModules: int
    errorModules: int
    disabledModules: int
    containerStats: dict
    loaderStats: dict


def _build_module_response(module_info) -> ModuleInfoResponse:
    """Converte ModuleInfo para response."""
    return ModuleInfoResponse(
        id=module_info.id,
        name=module_info.name,
        kind=module_info.kind,
        version=module_info.version,
        status=module_info.status,
        displayOrder=module_info.display_order,
        description=module_info.description,
        author=module_info.author,
        icon=module_info.icon,
        manifest=module_info.manifest,
        config=module_info.config,
        installedAt=module_info.installed_at,
        lastLoadedAt=module_info.last_loaded_at,
        lastErrorAt=module_info.last_error_at,
        errorMessage=module_info.error_message,
        loadCount=module_info.load_count,
        createdAt=module_info.created_at,
        updatedAt=module_info.updated_at,
    )


# =========================
#   MODULE MANAGEMENT
# =========================
@router.get("/", response_model=List[ModuleInfoResponse])
async def list_modules(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    current: CurrentUser = Depends(require_admin)
):
    """Lista todos os módulos registrados no sistema."""
    logger.info("admin.list_modules.start", extra={"status": status, "admin_id": current["sub"]})
    
    modules = await registry_service.list_modules(status=status)
    
    logger.info("admin.list_modules.ok", extra={"count": len(modules), "status": status})
    return [_build_module_response(m) for m in modules]


@router.get("/{module_id}", response_model=ModuleInfoResponse)
async def get_module(
    module_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Detalhes completos de um módulo específico."""
    logger.info("admin.get_module.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    module = await registry_service.get_module(module_id)
    if not module:
        raise HTTPException(404, detail="Módulo não encontrado")
    
    logger.info("admin.get_module.ok", extra={"module_id": module_id})
    return _build_module_response(module)


@router.post("/register", response_model=ModuleInfoResponse, status_code=201)
async def register_module(
    body: RegisterModuleRequest,
    current: CurrentUser = Depends(require_admin)
):
    """Registra novo módulo no sistema."""
    module_id = body.manifest.get("id", "unknown")
    logger.info("admin.register_module.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    try:
        module = await registry_service.register_module(
            manifest=body.manifest,
            config=body.config
        )
        
        logger.info("admin.register_module.ok", extra={"module_id": module_id})
        return _build_module_response(module)
        
    except ModuleError as e:
        logger.info("admin.register_module.fail", extra={"module_id": module_id, "error": e.code})
        raise HTTPException(400, detail=e.message)
    except Exception as e:
        logger.error("admin.register_module.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro interno registrando módulo")


# =========================
#   MODULE CONTROL
# =========================
@router.post("/{module_id}/enable", response_model=ModuleActionResponse)
async def enable_module(
    module_id: str,
    current: CurrentUser = Depends(require_admin),
    request: Request
):
    """
    Ativa um módulo (carrega services + routes).
    
    ATENÇÃO: Para carregar routes, pode ser necessário restart do FastAPI.
    """
    logger.info("admin.enable_module.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    try:
        # Verificar se módulo existe
        module = await registry_service.get_module(module_id)
        if not module:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        if module.status == "active":
            return ModuleActionResponse(
                success=True,
                message="Módulo já está ativo",
                moduleId=module_id
            )
        
        # Tentar ativar (se loader estiver disponível)
        if hasattr(request.app.state, "module_loader"):
            loader = request.app.state.module_loader
            success = await loader.load_module(module)
            
            if success:
                message = "Módulo ativado com sucesso"
            else:
                message = "Falha ativando módulo - verificar logs"
        else:
            # Fallback: apenas marcar como ativo no registry
            await registry_service.set_module_status(module_id, "active")
            success = True
            message = "Módulo marcado como ativo (restart necessário para carregar routes)"
        
        logger.info("admin.enable_module.ok", extra={"module_id": module_id, "success": success})
        
        return ModuleActionResponse(
            success=success,
            message=message,
            moduleId=module_id
        )
        
    except ModuleError as e:
        logger.info("admin.enable_module.fail", extra={"module_id": module_id, "error": e.code})
        raise HTTPException(400, detail=e.message)
    except Exception as e:
        logger.error("admin.enable_module.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro interno ativando módulo")


@router.post("/{module_id}/disable", response_model=ModuleActionResponse)
async def disable_module(
    module_id: str,
    current: CurrentUser = Depends(require_admin),
    request: Request
):
    """
    Desativa um módulo (remove services, routes ficam até restart).
    """
    logger.info("admin.disable_module.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    try:
        # Verificar se módulo existe
        module = await registry_service.get_module(module_id)
        if not module:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        # Não permitir desativar módulos system críticos
        if module.kind == "system" and module_id in ["auth", "users"]:
            raise HTTPException(400, detail="Não é possível desativar módulos críticos do sistema")
        
        # Tentar desativar
        if hasattr(request.app.state, "module_loader"):
            loader = request.app.state.module_loader
            success = await loader.unload_module(module_id)
            message = "Módulo desativado com sucesso" if success else "Falha desativando módulo"
        else:
            # Fallback: apenas marcar como disabled
            await registry_service.set_module_status(module_id, "disabled")
            success = True
            message = "Módulo marcado como desativado"
        
        logger.info("admin.disable_module.ok", extra={"module_id": module_id, "success": success})
        
        return ModuleActionResponse(
            success=success,
            message=message,
            moduleId=module_id
        )
        
    except Exception as e:
        logger.error("admin.disable_module.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro interno desativando módulo")


@router.post("/{module_id}/reload", response_model=ModuleActionResponse)
async def reload_module(
    module_id: str,
    current: CurrentUser = Depends(require_admin),
    request: Request
):
    """
    Recarrega um módulo (unload + load para aplicar mudanças).
    """
    logger.info("admin.reload_module.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    try:
        if not hasattr(request.app.state, "module_loader"):
            raise HTTPException(503, detail="Module loader não disponível - restart necessário")
        
        loader = request.app.state.module_loader
        success = await loader.reload_module(module_id)
        
        message = "Módulo recarregado com sucesso" if success else "Falha recarregando módulo"
        
        logger.info("admin.reload_module.ok", extra={"module_id": module_id, "success": success})
        
        return ModuleActionResponse(
            success=success,
            message=message,
            moduleId=module_id
        )
        
    except Exception as e:
        logger.error("admin.reload_module.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro interno recarregando módulo")


# =========================
#   CONFIGURATION  
# =========================
@router.get("/{module_id}/config")
async def get_module_config(
    module_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Obtém configuração atual de um módulo."""
    logger.info("admin.get_config.start", extra={"module_id": module_id})
    
    config = await registry_service.get_config(module_id)
    if config is None:
        raise HTTPException(404, detail="Módulo não encontrado")
    
    return {"moduleId": module_id, "config": config}


@router.put("/{module_id}/config", response_model=ModuleActionResponse)
async def update_module_config(
    module_id: str,
    body: UpdateConfigRequest,
    current: CurrentUser = Depends(require_admin)
):
    """
    Atualiza configuração de um módulo.
    
    ATENÇÃO: Para aplicar mudanças nos services, use /reload após atualizar config.
    """
    logger.info("admin.update_config.start", extra={"module_id": module_id, "admin_id": current["sub"]})
    
    try:
        success = await registry_service.update_config(module_id, body.config)
        
        if not success:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        logger.info("admin.update_config.ok", extra={"module_id": module_id})
        
        return ModuleActionResponse(
            success=True,
            message="Configuração atualizada (use /reload para aplicar nos services)",
            moduleId=module_id
        )
        
    except Exception as e:
        logger.error("admin.update_config.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro interno atualizando configuração")


# =========================
#   HEALTH & MONITORING
# =========================  
@router.get("/{module_id}/health")
async def module_health(
    module_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Health check específico de um módulo."""
    logger.info("admin.health_check.start", extra={"module_id": module_id})
    
    try:
        # Verificar se módulo existe no registry
        module = await registry_service.get_module(module_id)
        if not module:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        # Health check via service container
        container_health = await container.health_check()
        service_name = f"{module_id}_service"
        
        if service_name in container_health:
            service_health = container_health[service_name]
        else:
            service_health = {
                "status": "unknown",
                "message": "Service não encontrado no container"
            }
        
        # Registrar health check no registry
        await registry_service.record_health_check(
            module_id=module_id,
            check_type="manual",
            status=service_health["status"],
            message=service_health.get("message"),
            response_time_ms=service_health.get("response_time_ms")
        )
        
        result = {
            "moduleId": module_id,
            "status": module.status,
            "serviceHealth": service_health,
            "lastLoaded": module.last_loaded_at,
            "loadCount": module.load_count,
            "errorMessage": module.error_message
        }
        
        logger.info("admin.health_check.ok", extra={"module_id": module_id, "health": service_health["status"]})
        return result
        
    except Exception as e:
        logger.error("admin.health_check.error", extra={"module_id": module_id, "error": str(e)})
        raise HTTPException(500, detail="Erro verificando health do módulo")


@router.get("/stats", response_model=ModuleStatsResponse)
async def module_system_stats(
    current: CurrentUser = Depends(require_admin),
    request: Request
):
    """Estatísticas gerais do sistema de módulos."""
    logger.info("admin.system_stats.start", extra={"admin_id": current["sub"]})
    
    try:
        # Stats do registry
        all_modules = await registry_service.list_modules()
        
        stats_by_status = {}
        for module in all_modules:
            stats_by_status[module.status] = stats_by_status.get(module.status, 0) + 1
        
        # Stats do container
        container_stats = container.get_stats()
        
        # Stats do loader (se disponível)
        loader_stats = {}
        if hasattr(request.app.state, "module_loader"):
            loader = request.app.state.module_loader
            loader_stats = await loader.get_loader_stats()
        
        result = ModuleStatsResponse(
            totalModules=len(all_modules),
            activeModules=stats_by_status.get("active", 0),
            errorModules=stats_by_status.get("error", 0),
            disabledModules=stats_by_status.get("disabled", 0),
            containerStats=container_stats,
            loaderStats=loader_stats
        )
        
        logger.info("admin.system_stats.ok", extra={"total": len(all_modules)})
        return result
        
    except Exception as e:
        logger.error("admin.system_stats.error", extra={"error": str(e)})
        raise HTTPException(500, detail="Erro obtendo estatísticas")


# =========================
#   DEPENDENCIES
# =========================
@router.get("/{module_id}/dependencies")
async def get_module_dependencies(
    module_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Lista dependências de um módulo."""
    logger.info("admin.get_dependencies.start", extra={"module_id": module_id})
    
    # Verificar se módulo existe
    module = await registry_service.get_module(module_id)
    if not module:
        raise HTTPException(404, detail="Módulo não encontrado")
    
    dependencies = await registry_service.get_dependencies(module_id)
    
    result = {
        "moduleId": module_id,
        "dependencies": [
            {
                "dependsOn": dep.depends_on,
                "versionMin": dep.version_min,
                "versionMax": dep.version_max,
                "required": dep.required
            }
            for dep in dependencies
        ]
    }
    
    logger.info("admin.get_dependencies.ok", extra={"module_id": module_id, "count": len(dependencies)})
    return result


# =========================
#   SERVICE CONTAINER INSPECTION
# =========================
@router.get("/{module_id}/services")
async def get_module_services(
    module_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Lista services registrados para um módulo."""
    logger.info("admin.get_services.start", extra={"module_id": module_id})
    
    service_names = container.get_module_services(module_id)
    services_info = []
    
    for service_name in service_names:
        definition = container.get_service_info(service_name)
        instance = container.get_instance_info(service_name)
        
        service_info = {
            "name": service_name,
            "class": definition.service_class.__name__,
            "singleton": definition.singleton,
            "dependencies": definition.dependencies,
            "instanceCount": definition.instance_count,
            "lastCreated": definition.last_created_at,
            "errorMessage": definition.error_message
        }
        
        if instance:
            service_info.update({
                "instanceId": instance.instance_id,
                "requestCount": instance.request_count,
                "createdAt": instance.created_at
            })
        
        services_info.append(service_info)
    
    result = {
        "moduleId": module_id,
        "services": services_info,
        "totalServices": len(services_info)
    }
    
    logger.info("admin.get_services.ok", extra={"module_id": module_id, "count": len(services_info)})
    return result


# =========================
#   SYSTEM OPERATIONS
# =========================
@router.post("/system/reload-all", response_model=Dict[str, bool])
async def reload_all_modules(
    current: CurrentUser = Depends(require_admin),
    request: Request
):
    """
    Recarrega todos os módulos ativos.
    
    CUIDADO: Operação pesada que pode impactar performance.
    """
    logger.info("admin.reload_all.start", extra={"admin_id": current["sub"]})
    
    try:
        if not hasattr(request.app.state, "module_loader"):
            raise HTTPException(503, detail="Module loader não disponível")
        
        loader = request.app.state.module_loader
        
        # Obter módulos ativos
        active_modules = await registry_service.list_modules(status="active")
        
        results = {}
        for module in active_modules:
            try:
                success = await loader.reload_module(module.id)
                results[module.id] = success
            except Exception as e:
                results[module.id] = False
                logger.error("reload_all.module_failed", extra={
                    "module_id": module.id, 
                    "error": str(e)
                })
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info("admin.reload_all.completed", extra={
            "total": total,
            "successful": successful,
            "failed": total - successful
        })
        
        return results
        
    except Exception as e:
        logger.error("admin.reload_all.error", extra={"error": str(e)})
        raise HTTPException(500, detail="Erro recarregando módulos")


@router.get("/system/container-stats")
async def container_stats(
    current: CurrentUser = Depends(require_admin)
):
    """Estatísticas detalhadas do service container."""
    logger.info("admin.container_stats.start", extra={"admin_id": current["sub"]})
    
    try:
        stats = container.get_stats()
        health = await container.health_check()
        
        result = {
            "stats": stats,
            "health": health,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return result
        
    except Exception as e:
        logger.error("admin.container_stats.error", extra={"error": str(e)})
        raise HTTPException(500, detail="Erro obtendo stats do container")


# =========================
#   ERROR HANDLING
# =========================
@router.exception_handler(ModuleError)
async def module_error_handler(request: Request, exc: ModuleError):
    """Handler para erros específicos de módulos."""
    logger.info("module_error", extra={
        "error_code": exc.code,
        "message": exc.message,
        "details": exc.details
    })
    
    status_map = {
        "ERR_MODULE_NOT_FOUND": 404,
        "ERR_MODULE_EXISTS": 400,
        "ERR_INVALID_MANIFEST": 400,
        "ERR_DEPENDENCY_NOT_ACTIVE": 400,
        "ERR_INVALID_KIND": 400,
    }
    
    status_code = status_map.get(exc.code, 400)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "traceId": request.headers.get("X-Trace-ID")
        }
    )


# =========================
#   DESENVOLVIMENTO/DEBUG
# =========================
@router.get("/debug/filesystem")
async def debug_filesystem_modules(
    current: CurrentUser = Depends(require_admin)
):
    """
    [DEBUG] Compara módulos no filesystem vs registry.
    
    Útil para desenvolvimento e troubleshooting.
    """
    from pathlib import Path
    
    logger.info("admin.debug_filesystem.start", extra={"admin_id": current["sub"]})
    
    try:
        # Módulos no filesystem
        api_path = Path("app/app/api")
        filesystem_modules = []
        
        if api_path.exists():
            for module_dir in api_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith("_"):
                    routes_file = module_dir / "routes.py"
                    schemas_file = module_dir / "schemas.py"
                    
                    filesystem_modules.append({
                        "id": module_dir.name,
                        "hasRoutes": routes_file.exists(),
                        "hasSchemas": schemas_file.exists(),
                        "path": str(module_dir)
                    })
        
        # Módulos no registry
        registry_modules = await registry_service.list_modules()
        registry_ids = {m.id for m in registry_modules}
        filesystem_ids = {m["id"] for m in filesystem_modules}
        
        # Comparação
        in_both = registry_ids & filesystem_ids
        only_registry = registry_ids - filesystem_ids  
        only_filesystem = filesystem_ids - registry_ids
        
        result = {
            "filesystem": filesystem_modules,
            "registry": [{"id": m.id, "status": m.status, "version": m.version} for m in registry_modules],
            "comparison": {
                "inBoth": list(in_both),
                "onlyInRegistry": list(only_registry),
                "onlyInFilesystem": list(only_filesystem),
                "total": {
                    "filesystem": len(filesystem_ids),
                    "registry": len(registry_ids)
                }
            }
        }
        
        logger.info("admin.debug_filesystem.ok", extra={
            "filesystem_count": len(filesystem_ids),
            "registry_count": len(registry_ids)
        })
        
        return result
        
    except Exception as e:
        logger.error("admin.debug_filesystem.error", extra={"error": str(e)})
        raise HTTPException(500, detail="Erro analisando filesystem")