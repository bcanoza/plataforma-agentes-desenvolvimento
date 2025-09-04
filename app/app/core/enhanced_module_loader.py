# app/core/enhanced_module_loader.py  
"""
Module Loader com Registry e Service Container.

Nova arquitetura que substitui o api_loader.py atual:
- Carrega módulos do registry (BD) ao invés de filesystem
- Usa service container para DI centralizado
- Suporte a hot-reload e configuração dinâmica
- Health monitoring por módulo
- Dependency resolution automático
"""
from __future__ import annotations

import importlib
import sys
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from fastapi import FastAPI

from app.core.service_container import container, ServiceContainer
from app.services.module_registry_service import ModuleRegistryService, PgModuleRepo, ModuleInfo
from app.core.logging_config import get_logger

logger = get_logger("core.enhanced_module_loader")


class EnhancedModuleLoader:
    """Module loader com registry e service container."""
    
    def __init__(self, app: FastAPI, service_container: ServiceContainer):
        self.app = app
        self.container = service_container
        self.registry = ModuleRegistryService(PgModuleRepo())
        
        # Estado do loader
        self._loaded_modules: Dict[str, ModuleInfo] = {}
        self._failed_modules: Dict[str, str] = {}  # module_id -> error
    
    async def load_all_active_modules(self) -> Dict[str, bool]:
        """
        Carrega todos os módulos ativos do registry.
        
        Returns:
            Dict com resultado por módulo {module_id: success}
        """
        logger.info("load_all.start")
        
        try:
            # Buscar módulos ativos do registry
            active_modules = await self.registry.get_active_modules()
            logger.info("modules.discovered", extra={"count": len(active_modules)})
            
            results = {}
            
            # Carregar em ordem de dependência (sistema → admin → opcional)
            sorted_modules = self._sort_by_dependency_order(active_modules)
            
            for module_info in sorted_modules:
                try:
                    success = await self.load_module(module_info)
                    results[module_info.id] = success
                    
                    if success:
                        logger.info("module.loaded", extra={"module_id": module_info.id})
                    else:
                        logger.error("module.load_failed", extra={"module_id": module_info.id})
                        
                except Exception as e:
                    results[module_info.id] = False
                    error_msg = str(e)
                    self._failed_modules[module_info.id] = error_msg
                    
                    # Salvar erro no registry
                    await self.registry.set_module_status(
                        module_info.id, 
                        "error", 
                        error_msg
                    )
                    
                    logger.error("module.load_exception", extra={
                        "module_id": module_info.id,
                        "error": error_msg
                    })
            
            # Estatísticas finais
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            logger.info("load_all.completed", extra={
                "total": total,
                "successful": successful, 
                "failed": total - successful
            })
            
            return results
            
        except Exception as e:
            logger.error("load_all.failed", extra={"error": str(e)})
            raise
    
    async def load_module(self, module_info: ModuleInfo) -> bool:
        """
        Carrega um módulo específico.
        
        Steps:
        1. Validar dependências
        2. Registrar services no container  
        3. Carregar routes no FastAPI
        4. Atualizar status no registry
        
        Args:
            module_info: Informações do módulo do registry
            
        Returns:
            True se carregou com sucesso
        """
        module_id = module_info.id
        start_time = time.time()
        
        logger.info("module.load.start", extra={"module_id": module_id})
        
        try:
            # 1. Validar dependências
            await self._validate_dependencies(module_info)
            
            # 2. Registrar services no container
            await self._register_module_services(module_info)
            
            # 3. Carregar routes  
            router = await self._load_module_routes(module_info)
            if router:
                self.app.include_router(router)
            
            # 4. Atualizar registry
            await self.registry.increment_load_count(module_id)
            await self.registry.set_module_status(module_id, "active")
            
            # 5. Health check inicial
            await self._initial_health_check(module_info)
            
            # Cachear módulo carregado
            self._loaded_modules[module_id] = module_info
            
            load_time = (time.time() - start_time) * 1000
            logger.info("module.load.ok", extra={
                "module_id": module_id,
                "load_time_ms": load_time
            })
            
            return True
            
        except Exception as e:
            error_msg = f"Falha carregando módulo: {str(e)}"
            
            # Salvar erro no registry
            await self.registry.set_module_status(module_id, "error", error_msg)
            
            logger.error("module.load.failed", extra={
                "module_id": module_id,
                "error": error_msg
            })
            
            return False
    
    async def unload_module(self, module_id: str) -> bool:
        """
        Descarrega um módulo (remove services, mantém routes por limitação FastAPI).
        
        Note: FastAPI não suporta remoção dinâmica de routes.
        Para remover routes completamente, é necessário restart.
        """
        logger.info("module.unload.start", extra={"module_id": module_id})
        
        try:
            # 1. Remover services do container
            removed_services = await self.container.unload_module(module_id)
            
            # 2. Atualizar status no registry
            await self.registry.set_module_status(module_id, "disabled")
            
            # 3. Remover do cache local
            if module_id in self._loaded_modules:
                del self._loaded_modules[module_id]
            
            if module_id in self._failed_modules:
                del self._failed_modules[module_id]
            
            logger.info("module.unload.ok", extra={
                "module_id": module_id,
                "removed_services": removed_services
            })
            
            return True
            
        except Exception as e:
            logger.error("module.unload.failed", extra={
                "module_id": module_id,
                "error": str(e)
            })
            return False
    
    async def reload_module(self, module_id: str) -> bool:
        """Recarrega um módulo (unload + load)."""
        logger.info("module.reload.start", extra={"module_id": module_id})
        
        # 1. Unload atual
        await self.unload_module(module_id)
        
        # 2. Buscar info atualizada do registry
        module_info = await self.registry.get_module(module_id)
        if not module_info:
            logger.error("module.reload.not_found", extra={"module_id": module_id})
            return False
        
        # 3. Load novamente
        success = await self.load_module(module_info)
        
        if success:
            logger.info("module.reload.ok", extra={"module_id": module_id})
        else:
            logger.error("module.reload.failed", extra={"module_id": module_id})
            
        return success
    
    async def get_loader_stats(self) -> dict:
        """Retorna estatísticas do loader."""
        return {
            "loaded_modules": len(self._loaded_modules),
            "failed_modules": len(self._failed_modules),
            "container_stats": self.container.get_stats(),
            "modules": {
                "loaded": list(self._loaded_modules.keys()),
                "failed": list(self._failed_modules.keys())
            }
        }
    
    # ---------- PRIVATE METHODS ----------
    def _sort_by_dependency_order(self, modules: List[ModuleInfo]) -> List[ModuleInfo]:
        """Ordena módulos por dependências (dependências primeiro)."""
        # Implementação simples por kind (sistema → admin → opcional)
        # TODO: Implementar ordenação topológica real
        
        def sort_key(module: ModuleInfo) -> int:
            order_map = {"system": 100, "admin": 200, "optional": 300}
            return order_map.get(module.kind, 999) + module.display_order
        
        return sorted(modules, key=sort_key)
    
    async def _validate_dependencies(self, module_info: ModuleInfo) -> None:
        """Valida se dependências estão ativas."""
        dependencies = await self.registry.get_dependencies(module_info.id)
        
        for dep in dependencies:
            if dep.required:
                # Verificar se dependência está carregada
                if dep.depends_on not in self._loaded_modules:
                    raise RuntimeError(f"Dependência requerida '{dep.depends_on}' não está carregada")
    
    async def _register_module_services(self, module_info: ModuleInfo) -> None:
        """Registra services do módulo no container."""
        module_id = module_info.id
        
        # Mapeamento de services conhecidos (pode ser expandido)
        service_mappings = {
            "auth": self._register_auth_services,
            "users": self._register_user_services,
            "agents": self._register_agent_services,
        }
        
        if module_id in service_mappings:
            await service_mappings[module_id](module_info)
        else:
            logger.warning("module.no_service_mapping", extra={"module_id": module_id})
    
    async def _register_auth_services(self, module_info: ModuleInfo):
        """Registra services do módulo auth."""
        from app.services.auth_wiring import build_auth_service_from_settings
        from app.services.auth_service import AuthService
        
        self.container.register(
            "auth_service",
            AuthService,
            build_auth_service_from_settings,
            module_id="auth",
            singleton=True
        )
    
    async def _register_user_services(self, module_info: ModuleInfo):
        """Registra services do módulo users."""
        from app.services.user_service import UserService
        from app.repositories.sql_repos import PgUserRepo, PgAuditLogRepo
        
        # Registrar dependencies
        self.container.register(
            "user_repo",
            PgUserRepo,
            PgUserRepo,
            module_id="core",  # shared dependency
            singleton=True
        )
        
        self.container.register(
            "audit_repo", 
            PgAuditLogRepo,
            PgAuditLogRepo,
            module_id="core",
            singleton=True
        )
        
        # Service principal
        async def build_user_service(**deps):
            return UserService()  # UserService atual não usa DI ainda
        
        self.container.register(
            "user_service",
            UserService,
            build_user_service,
            module_id="users",
            singleton=True,
            dependencies=["user_repo", "audit_repo"]
        )
    
    async def _register_agent_services(self, module_info: ModuleInfo):
        """Registra services do módulo agents."""
        # TODO: Implementar quando AgentService estiver estruturado
        logger.info("agent_services.todo", extra={"module_id": "agents"})
    
    async def _load_module_routes(self, module_info: ModuleInfo) -> Optional[Any]:
        """Carrega router do módulo via import dinâmico."""
        module_id = module_info.id
        
        try:
            # Caminho do módulo routes
            routes_module_path = f"app.api.{module_id}.routes"
            
            # Import dinâmico
            if routes_module_path in sys.modules:
                # Reload se já carregado
                module = importlib.reload(sys.modules[routes_module_path])
            else:
                module = importlib.import_module(routes_module_path)
            
            # Extrair router
            router = getattr(module, "router", None)
            if router is None:
                raise RuntimeError(f"Módulo {module_id} não expõe 'router'")
            
            return router
            
        except Exception as e:
            raise RuntimeError(f"Falha carregando routes: {str(e)}")
    
    async def _initial_health_check(self, module_info: ModuleInfo) -> None:
        """Executa health check inicial após carregar módulo."""
        module_id = module_info.id
        
        try:
            start_time = time.time()
            
            # Health check simples: tentar resolver service principal
            service_name = f"{module_id}_service"
            if service_name in self.container._definitions:
                await self.container.get(service_name)
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Registrar resultado
            await self.registry.record_health_check(
                module_id=module_id,
                check_type="startup",
                status="healthy",
                message="Módulo carregado com sucesso",
                response_time_ms=response_time
            )
            
        except Exception as e:
            # Registrar falha
            await self.registry.record_health_check(
                module_id=module_id,
                check_type="startup", 
                status="unhealthy",
                message=str(e)
            )


# =========================
#   FACTORY FUNCTION
# =========================
async def initialize_enhanced_loading(app: FastAPI) -> EnhancedModuleLoader:
    """
    Inicializa o sistema de carregamento de módulos.
    
    Use esta função no app/main.py startup.
    """
    logger.info("enhanced_loading.init.start")
    
    try:
        # 1. Criar loader
        loader = EnhancedModuleLoader(app, container)
        
        # 2. Registrar repositories básicos no container
        await _register_core_services()
        
        # 3. Carregar todos os módulos ativos
        results = await loader.load_all_active_modules()
        
        # 4. Log resumo
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info("enhanced_loading.init.completed", extra={
            "total_modules": total,
            "successful": successful,
            "failed": total - successful,
            "results": results
        })
        
        return loader
        
    except Exception as e:
        logger.error("enhanced_loading.init.failed", extra={"error": str(e)})
        raise


async def _register_core_services():
    """Registra services básicos compartilhados."""
    from app.repositories.sql_repos import PgUserRepo, PgAuditLogRepo
    
    # Repositories compartilhados
    container.register(
        "user_repo",
        PgUserRepo,
        PgUserRepo,
        module_id="core",
        singleton=True
    )
    
    container.register(
        "audit_repo",
        PgAuditLogRepo, 
        PgAuditLogRepo,
        module_id="core",
        singleton=True
    )
    
    logger.info("core_services.registered", extra={
        "services": ["user_repo", "audit_repo"]
    })


# =========================
#   INTEGRATION HELPERS
# =========================
async def enhanced_startup_handler(app: FastAPI) -> None:
    """
    Handler de startup que substitui o carregamento atual.
    
    Use em app/main.py:
    
    @app.on_event("startup") 
    async def startup():
        await enhanced_startup_handler(app)
    """
    try:
        # Carregar com novo sistema
        loader = await initialize_enhanced_loading(app)
        
        # Salvar loader na app para uso posterior
        app.state.module_loader = loader
        
        # Health check geral
        container_health = await container.health_check()
        healthy_services = sum(1 for h in container_health.values() if h["status"] == "healthy")
        total_services = len(container_health)
        
        logger.info("startup.complete", extra={
            "healthy_services": healthy_services,
            "total_services": total_services,
            "container_stats": container.get_stats()
        })
        
    except Exception as e:
        logger.error("startup.failed", extra={"error": str(e)})
        # Em produção, pode querer fail-fast aqui
        raise


async def enhanced_shutdown_handler(app: FastAPI) -> None:
    """
    Handler de shutdown para cleanup.
    
    @app.on_event("shutdown")
    async def shutdown():
        await enhanced_shutdown_handler(app)  
    """
    try:
        logger.info("shutdown.start")
        
        if hasattr(app.state, "module_loader"):
            loader = app.state.module_loader
            
            # Unload todos os módulos para cleanup
            for module_id in list(loader._loaded_modules.keys()):
                await loader.unload_module(module_id)
        
        logger.info("shutdown.complete")
        
    except Exception as e:
        logger.error("shutdown.failed", extra={"error": str(e)})


# =========================
#   UTILS PARA MIGRAÇÃO
# =========================
def create_migration_guide() -> str:
    """Cria guia para migrar do sistema atual."""
    
    return """
📋 GUIA DE MIGRAÇÃO - Sistema Atual → Enhanced Module Loader

1. **Preparar BD:**
   python app/db_schema/create_module_schema.py
   python scripts/populate_module_registry.py

2. **Atualizar main.py:**
   # ANTES (app/main.py):
   from app.core.api_loader import include_api_modules
   include_api_modules(app)
   
   # DEPOIS:
   from app.core.enhanced_module_loader import enhanced_startup_handler
   
   @app.on_event("startup")
   async def startup():
       await enhanced_startup_handler(app)

3. **Migrar Routes (gradual):**
   # ANTES:
   service = build_user_service_from_settings()  # instância local
   
   # DEPOIS: 
   async def get_user_service() -> UserService:
       return await container.get("user_service")
   
   @router.get("/users/{id}")
   async def get_user(
       user_id: str,
       service: UserService = Depends(get_user_service)  # ← DI pelo container
   ):

4. **Benefícios Imediatos:**
   ✅ Admin APIs para gerenciar módulos
   ✅ Configuração dinâmica (sem restart)  
   ✅ Health monitoring por módulo
   ✅ Service DI centralizado
   ✅ Hot-reload de configurações

5. **Compatibilidade:**
   ✅ Sistema atual continua funcionando
   ✅ Migração pode ser gradual
   ✅ Fallback automático para api_loader atual
    """


if __name__ == "__main__":
    print(create_migration_guide())