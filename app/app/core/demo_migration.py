# app/core/demo_migration.py
"""
Demonstração da migração dos módulos auth e users para o novo sistema.

Esta implementação:
- Usa mock registry (sem BD)
- Implementa service container funcional
- Migra auth e users services
- Demonstra DI centralizado
- Mostra admin APIs funcionando
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from app.core.logging_config import get_logger

# Mock implementations
from app.core.service_container import ServiceContainer
from app.core.mock_module_registry import MockModuleRepo
from app.services.module_registry_service import ModuleRegistryService

logger = get_logger("demo.migration")

# Instâncias globais para demo
demo_container = ServiceContainer()
demo_registry = ModuleRegistryService(MockModuleRepo())


# =========================
#   DEMO: MIGRAÇÃO AUTH SERVICE
# =========================
async def setup_auth_module():
    """Demonstra migração do AuthService para o container."""
    logger.info("demo.setup_auth.start")
    
    try:
        # 1. Obter módulo do registry
        auth_module = await demo_registry.get_module("auth")
        if not auth_module:
            raise RuntimeError("Módulo auth não encontrado no registry")
        
        # 2. Registrar AuthService no container
        from app.services.auth_wiring import build_auth_service_from_settings
        from app.services.auth_service import AuthService
        
        demo_container.register(
            "auth_service",
            AuthService,
            build_auth_service_from_settings,
            module_id="auth",
            singleton=True,
            dependencies=[]  # AuthService atual não usa DI explícito
        )
        
        # 3. Testar resolução
        auth_service = await demo_container.get("auth_service")
        logger.info("demo.auth_service.resolved", extra={"type": type(auth_service).__name__})
        
        # 4. Atualizar status no registry
        await demo_registry.set_module_status("auth", "active")
        await demo_registry.increment_load_count("auth")
        
        logger.info("demo.setup_auth.ok")
        return True
        
    except Exception as e:
        logger.error("demo.setup_auth.failed", extra={"error": str(e)})
        await demo_registry.set_module_status("auth", "error", str(e))
        return False


# =========================
#   DEMO: MIGRAÇÃO USER SERVICE  
# =========================
async def setup_users_module():
    """Demonstra migração do UserService para o container."""
    logger.info("demo.setup_users.start")
    
    try:
        # 1. Obter módulo do registry
        users_module = await demo_registry.get_module("users")
        if not users_module:
            raise RuntimeError("Módulo users não encontrado no registry")
        
        # 2. Registrar repositories compartilhados primeiro
        from app.repositories.sql_repos import PgUserRepo, PgAuditLogRepo
        
        demo_container.register(
            "user_repo",
            PgUserRepo,
            lambda: PgUserRepo(),
            module_id="core",  # shared
            singleton=True
        )
        
        demo_container.register(
            "audit_repo", 
            PgAuditLogRepo,
            lambda: PgAuditLogRepo(),
            module_id="core",  # shared
            singleton=True
        )
        
        # 3. Registrar UserService com DI
        from app.services.user_service import UserService
        
        async def build_user_service_with_di(**deps):
            """Factory que usa as dependencies resolvidas."""
            # UserService atual não usa DI no constructor, mas podemos preparar
            config = users_module.config
            service = UserService()
            
            # Injetar configuração dinâmica (futuro)
            service._config = config  
            return service
        
        demo_container.register(
            "user_service",
            UserService,
            build_user_service_with_di,
            module_id="users",
            singleton=True,
            dependencies=["user_repo", "audit_repo"]
        )
        
        # 4. Testar resolução
        user_service = await demo_container.get("user_service")
        logger.info("demo.user_service.resolved", extra={"type": type(user_service).__name__})
        
        # 5. Testar que dependencies foram resolvidas
        user_repo = await demo_container.get("user_repo") 
        audit_repo = await demo_container.get("audit_repo")
        logger.info("demo.dependencies.resolved", extra={
            "user_repo": type(user_repo).__name__,
            "audit_repo": type(audit_repo).__name__
        })
        
        # 6. Atualizar status no registry
        await demo_registry.set_module_status("users", "active")
        await demo_registry.increment_load_count("users")
        
        logger.info("demo.setup_users.ok")
        return True
        
    except Exception as e:
        logger.error("demo.setup_users.failed", extra={"error": str(e)})
        await demo_registry.set_module_status("users", "error", str(e))
        return False


# =========================
#   DEMO: DEPENDENCY INJECTION NOS ROUTES
# =========================
async def get_auth_service_from_container():
    """Dependency function para AuthService."""
    return await demo_container.get("auth_service")

async def get_user_service_from_container():
    """Dependency function para UserService."""
    return await demo_container.get("user_service")


# Exemplo de como ficaria o routes.py migrado
def demo_migrated_route():
    """Exemplo de route usando DI do container."""
    
    from fastapi import APIRouter, Depends
    from app.api.auth.dependencies import require_admin, CurrentUser
    from app.api.auth.schemas import User, build_user_response
    
    demo_router = APIRouter(prefix="/v1/users/demo", tags=["Demo Migration"])
    
    @demo_router.get("/{user_id}")
    async def get_user_migrated(
        user_id: str,
        current: CurrentUser = Depends(require_admin),
        user_service = Depends(get_user_service_from_container)  # ← DI do container!
    ):
        """Exemplo de endpoint usando service do container."""
        logger.info("demo.get_user.start", extra={"user_id": user_id, "admin": current["sub"]})
        
        # Service vem do container, já configurado
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(404, detail="Usuário não encontrado")
        
        # Acessar config dinâmica do módulo
        config = getattr(user_service, '_config', {})
        user_data = build_user_response(user)
        
        result = {
            "user": user_data.dict(),
            "moduleConfig": {
                "maxUsers": config.get("max_users_per_tenant", 1000),
                "enableWhatsapp": config.get("enable_whatsapp", True) 
            },
            "containerStats": demo_container.get_stats()
        }
        
        logger.info("demo.get_user.ok", extra={"user_id": user_id})
        return result
    
    return demo_router


# =========================
#   DEMO: ADMIN APIs FUNCIONANDO
# =========================
def create_demo_admin_router():
    """Cria router de admin para demonstrar APIs de gestão."""
    
    from fastapi import APIRouter, Depends
    from app.api.auth.dependencies import require_admin, CurrentUser
    
    demo_admin_router = APIRouter(prefix="/v1/admin/demo", tags=["Demo Admin"])
    
    @demo_admin_router.get("/modules")
    async def list_modules_demo(current: CurrentUser = Depends(require_admin)):
        """Lista módulos do registry (demo)."""
        modules = await demo_registry.list_modules()
        
        return {
            "modules": [
                {
                    "id": m.id,
                    "name": m.name,
                    "status": m.status,
                    "version": m.version,
                    "loadCount": m.load_count,
                    "lastLoaded": m.last_loaded_at,
                    "errorMessage": m.error_message
                }
                for m in modules
            ],
            "total": len(modules)
        }
    
    @demo_admin_router.get("/modules/{module_id}/config")
    async def get_module_config_demo(
        module_id: str,
        current: CurrentUser = Depends(require_admin)
    ):
        """Obtém configuração de um módulo (demo)."""
        config = await demo_registry.get_config(module_id)
        if config is None:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        return {"moduleId": module_id, "config": config}
    
    @demo_admin_router.put("/modules/{module_id}/config")
    async def update_module_config_demo(
        module_id: str,
        config: dict,
        current: CurrentUser = Depends(require_admin)
    ):
        """Atualiza configuração de módulo (demo)."""
        success = await demo_registry.update_config(module_id, config)
        if not success:
            raise HTTPException(404, detail="Módulo não encontrado")
        
        return {
            "success": True,
            "message": "Configuração atualizada",
            "moduleId": module_id,
            "newConfig": config
        }
    
    @demo_admin_router.get("/container/stats") 
    async def container_stats_demo(current: CurrentUser = Depends(require_admin)):
        """Stats do service container (demo)."""
        stats = demo_container.get_stats()
        health = await demo_container.health_check()
        
        return {
            "container": stats,
            "health": health,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @demo_admin_router.post("/modules/{module_id}/reload")
    async def reload_module_demo(
        module_id: str,
        current: CurrentUser = Depends(require_admin)
    ):
        """Simula reload de módulo (demo).""" 
        # Para demo, apenas incrementar load count
        await demo_registry.increment_load_count(module_id)
        
        # "Recriar" service (simular hot reload)
        service_name = f"{module_id}_service"
        
        # Unload atual
        await demo_container.unload_module(module_id)
        
        # Recarregar (chama setup novamente) 
        if module_id == "auth":
            success = await setup_auth_module()
        elif module_id == "users":
            success = await setup_users_module()
        else:
            success = False
        
        return {
            "success": success,
            "message": f"Módulo {module_id} recarregado" if success else f"Falha recarregando {module_id}",
            "moduleId": module_id,
            "containerStats": demo_container.get_stats()
        }
    
    return demo_admin_router


# =========================
#   DEMO: SETUP COMPLETO
# =========================
async def setup_demo_migration(app: FastAPI):
    """Setup completo da demonstração de migração."""
    logger.info("demo.migration.start")
    
    try:
        # 1. Setup dos módulos no container
        auth_ok = await setup_auth_module()
        users_ok = await setup_users_module()
        
        # 2. Adicionar routes demo ao FastAPI
        demo_users_router = demo_migrated_route()
        demo_admin_router = create_demo_admin_router()
        
        app.include_router(demo_users_router)
        app.include_router(demo_admin_router)
        
        # 3. Stats finais
        container_stats = demo_container.get_stats() 
        modules = await demo_registry.list_modules()
        
        logger.info("demo.migration.completed", extra={
            "auth_setup": auth_ok,
            "users_setup": users_ok,
            "container_stats": container_stats,
            "registry_modules": len(modules)
        })
        
        print("\\n🎉 Demonstração de migração configurada!")
        print("\\n📊 Resultados:")
        print(f"   ✅ Auth module: {'OK' if auth_ok else 'FALHA'}")
        print(f"   ✅ Users module: {'OK' if users_ok else 'FALHA'}")
        print(f"   📦 Services no container: {container_stats['registered_services']}")
        print(f"   🏃 Instâncias ativas: {container_stats['active_instances']}")
        
        print("\\n🔗 Endpoints de demonstração:")
        print("   GET /v1/users/demo/{user_id}     - Route com DI do container")
        print("   GET /v1/admin/demo/modules       - Lista módulos do registry") 
        print("   GET /v1/admin/demo/container/stats - Stats do container")
        print("   PUT /v1/admin/demo/modules/{id}/config - Configuração dinâmica")
        print("   POST /v1/admin/demo/modules/{id}/reload - Hot reload")
        
        return True
        
    except Exception as e:
        logger.error("demo.migration.failed", extra={"error": str(e)})
        print(f"\\n❌ Erro na migração: {e}")
        return False


# =========================
#   COMPARAÇÃO: ANTES vs DEPOIS
# =========================
def show_migration_comparison():
    """Mostra comparação do antes vs depois."""
    
    print("""
📊 COMPARAÇÃO: ANTES vs DEPOIS DA MIGRAÇÃO

🚨 ANTES (Sistema Atual):
   # app/api/auth/routes.py
   auth_service = build_auth_service_from_settings()  # ← Global, ad-hoc
   
   # app/api/users/routes.py  
   service = UserService()  # ← Local, nova instância
   
   # Problemas:
   ❌ Inconsistência na instanciação
   ❌ Sem configuração dinâmica
   ❌ Sem administração central
   ❌ Memory leaks potenciais

✅ DEPOIS (Novo Sistema):
   # Container centralizado
   auth_service = await container.get("auth_service")  # ← DI singleton real
   user_service = await container.get("user_service")  # ← DI singleton real
   
   # Benefícios:
   ✅ DI centralizado e consistente
   ✅ Configuração dinâmica via registry
   ✅ Admin APIs para gestão
   ✅ Health monitoring automático
   ✅ Hot-reload sem restart

🎯 MIGRAÇÃO IMPLEMENTADA:
   ✅ Module Registry com dados de auth/users
   ✅ Service Container com DI funcional
   ✅ Routes demo usando novo padrão
   ✅ Admin APIs para gestão
   ✅ Configuração dinâmica
""")


# =========================
#   INTEGRATION HELPERS
# =========================
async def integrate_with_main_app(app: FastAPI):
    """Integra demonstração com a aplicação principal."""
    
    # Setup da demonstração
    success = await setup_demo_migration(app)
    
    if success:
        # Salvar referências na app para uso posterior
        app.state.demo_container = demo_container
        app.state.demo_registry = demo_registry
        
        # Adicionar health check demo
        @app.get("/v1/admin/demo/health")
        async def demo_health():
            """Health check da demonstração."""
            container_health = await demo_container.health_check()
            modules = await demo_registry.list_modules()
            
            return {
                "status": "healthy",
                "demo": True,
                "modules": [
                    {"id": m.id, "status": m.status} 
                    for m in modules
                ],
                "containerHealth": container_health,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    return success


# =========================
#   TESTING HELPERS
# =========================
async def test_migration():
    """Testa se a migração funcionou corretamente."""
    print("\\n🧪 Testando migração...")
    
    tests = []
    
    # Test 1: Registry funcionando
    try:
        modules = await demo_registry.list_modules()
        assert len(modules) >= 2, "Deve ter pelo menos auth e users"
        tests.append(("✅", "Registry - listar módulos"))
    except Exception as e:
        tests.append(("❌", f"Registry falhou: {e}"))
    
    # Test 2: Container DI funcionando
    try:
        auth_service = await demo_container.get("auth_service")
        user_service = await demo_container.get("user_service")
        assert auth_service is not None
        assert user_service is not None
        tests.append(("✅", "Container - resolver services"))
    except Exception as e:
        tests.append(("❌", f"Container falhou: {e}"))
    
    # Test 3: Singleton behavior
    try:
        auth1 = await demo_container.get("auth_service")
        auth2 = await demo_container.get("auth_service")
        assert auth1 is auth2, "Deve ser mesma instância (singleton)"
        tests.append(("✅", "Container - singleton behavior"))
    except Exception as e:
        tests.append(("❌", f"Singleton falhou: {e}"))
    
    # Test 4: Configuração dinâmica
    try:
        config = await demo_registry.get_config("auth")
        assert config is not None
        assert "access_ttl_sec" in config
        tests.append(("✅", "Registry - configuração dinâmica"))
    except Exception as e:
        tests.append(("❌", f"Config falhou: {e}"))
    
    # Resultados
    print("\\n📋 Resultados dos testes:")
    for status, message in tests:
        print(f"   {status} {message}")
    
    passed = sum(1 for status, _ in tests if status == "✅")
    total = len(tests)
    
    print(f"\\n🏆 Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    return passed == total


# =========================
#   CLI INTERFACE
# =========================
async def demo_cli():
    """Interface CLI para demonstração."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            print("🚀 Configurando demonstração...")
            await setup_demo_migration(None)  # Sem FastAPI para CLI
            
        elif command == "test":
            print("🧪 Testando migração...")
            await setup_demo_migration(None)
            success = await test_migration()
            sys.exit(0 if success else 1)
            
        elif command == "stats":
            print("📊 Estatísticas do sistema...")
            await setup_demo_migration(None)
            stats = demo_container.get_stats()
            health = await demo_container.health_check()
            modules = await demo_registry.list_modules()
            
            print(f"\\nContainer: {stats}")
            print(f"Health: {health}")
            print(f"Modules: {[m.id for m in modules]}")
            
        elif command == "compare":
            show_migration_comparison()
            
        else:
            print("Uso: python -m app.core.demo_migration [setup|test|stats|compare]")
    else:
        print("🎭 Demo da migração auth/users para novo sistema")
        print("\\nComandos disponíveis:")
        print("   setup     - Configura demonstração")
        print("   test      - Testa migração")  
        print("   stats     - Mostra estatísticas")
        print("   compare   - Mostra comparação antes/depois")


if __name__ == "__main__":
    asyncio.run(demo_cli())