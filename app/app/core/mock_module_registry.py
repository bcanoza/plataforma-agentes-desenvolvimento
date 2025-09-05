# app/core/mock_module_registry.py
"""
Mock implementation do Module Registry para demonstração.

Esta versão funciona em memória e será substituída pela versão com BD
quando a infraestrutura estiver configurada.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime, timezone
import json

from app.core.logging_config import get_logger
from app.services.module_registry_service import ModuleInfo, ModuleDependency

logger = get_logger("mock.module_registry")


class MockModuleRepo:
    """Repository mock para demonstração."""
    
    def __init__(self):
        # Dados dos módulos atuais baseados na análise do código
        self._modules: Dict[str, ModuleInfo] = {
            "auth": ModuleInfo(
                id="auth",
                name="Sistema de Autenticação",
                kind="system",
                version="1.0.0", 
                status="active",
                display_order=100,
                description="Autenticação JWT, sessões, reset de senha, API keys",
                author="Sistema",
                icon="shield",
                manifest={
                    "id": "auth",
                    "name": "Sistema de Autenticação",
                    "kind": "system",
                    "version": "1.0.0",
                    "order": 100,
                    "buttons": [],
                    "apis": [{
                        "id": "main",
                        "baseUrl": "/v1/auth",
                        "auth": "none",
                        "allowedPaths": ["*"],
                        "timeoutMs": 10000,
                        "rateLimit": {"maxRps": 10}
                    }],
                    "permissions": ["net:request"]
                },
                config={
                    "access_ttl_sec": 900,
                    "refresh_ttl_sec": 86400,
                    "rate_limit_login_per_ip": 5,
                    "enable_password_reset": True,
                    "jwt_algorithm": "RS256",
                    "cookie_secure": True,
                    "cookie_httponly": True
                },
                installed_at=datetime.now(timezone.utc).isoformat(),
                last_loaded_at=None,
                last_error_at=None,
                error_message=None,
                load_count=0,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat()
            ),
            
            "users": ModuleInfo(
                id="users",
                name="Gestão de Usuários", 
                kind="system",
                version="1.0.0",
                status="active",
                display_order=200,
                description="CRUD de usuários, perfis, preferências, gestão de permissões",
                author="Sistema",
                icon="account",
                manifest={
                    "id": "users",
                    "name": "Gestão de Usuários",
                    "kind": "system", 
                    "version": "1.0.0",
                    "order": 200,
                    "buttons": [{
                        "id": "my_profile",
                        "label": "Meu Perfil",
                        "route": "/profile", 
                        "icon": "account",
                        "order": 1
                    }],
                    "apis": [{
                        "id": "main",
                        "baseUrl": "/v1/users",
                        "auth": "core",
                        "allowedPaths": ["*"],
                        "timeoutMs": 5000,
                        "rateLimit": {"maxRps": 50}
                    }],
                    "permissions": ["net:request"]
                },
                config={
                    "password_min_length": 8,
                    "max_users_per_tenant": 1000,
                    "enable_self_registration": False,
                    "default_modules": ["auth", "workspace"],
                    "profile_fields_required": ["nome", "email"],
                    "enable_whatsapp": True
                },
                installed_at=datetime.now(timezone.utc).isoformat(),
                last_loaded_at=None,
                last_error_at=None,
                error_message=None,
                load_count=0,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat()
            )
        }
        
        # Dependências
        self._dependencies: List[ModuleDependency] = [
            ModuleDependency(
                module_id="users",
                depends_on="auth", 
                version_min=None,
                version_max=None,
                required=True
            )
        ]
    
    async def find_all(self) -> List[ModuleInfo]:
        """Lista todos os módulos."""
        return list(self._modules.values())
    
    async def find_by_id(self, module_id: str) -> Optional[ModuleInfo]:
        """Busca módulo por ID."""
        return self._modules.get(module_id)
    
    async def find_by_status(self, status: str) -> List[ModuleInfo]:
        """Lista módulos por status."""
        return [m for m in self._modules.values() if m.status == status]
    
    async def insert_module(self, **fields) -> ModuleInfo:
        """Insere novo módulo.""" 
        module_id = fields["id"]
        
        # Criar ModuleInfo
        now = datetime.now(timezone.utc).isoformat()
        module = ModuleInfo(
            id=module_id,
            name=fields["name"],
            kind=fields["kind"], 
            version=fields["version"],
            status=fields.get("status", "registered"),
            display_order=fields.get("display_order", 1000),
            description=fields.get("description"),
            author=fields.get("author"),
            icon=fields.get("icon"),
            manifest=fields["manifest"],
            config=fields.get("config", {}),
            installed_at=fields.get("installed_at", now),
            last_loaded_at=fields.get("last_loaded_at"),
            last_error_at=fields.get("last_error_at"),
            error_message=fields.get("error_message"),
            load_count=fields.get("load_count", 0),
            created_at=fields.get("created_at", now),
            updated_at=fields.get("updated_at", now)
        )
        
        self._modules[module_id] = module
        return module
    
    async def update_module(self, module_id: str, **fields) -> Optional[ModuleInfo]:
        """Atualiza módulo existente."""
        if module_id not in self._modules:
            return None
            
        module = self._modules[module_id]
        
        # Atualizar campos
        for key, value in fields.items():
            if value is not None:
                setattr(module, key.replace("_", ""), value)  # Ajuste para camelCase se necessário
        
        module.updated_at = datetime.now(timezone.utc).isoformat()
        return module
    
    async def delete_module(self, module_id: str) -> bool:
        """Remove módulo."""
        if module_id in self._modules:
            del self._modules[module_id]
            return True
        return False
    
    # ---------- DEPENDENCIES ----------
    async def get_dependencies(self, module_id: str) -> List[ModuleDependency]:
        """Retorna dependências de um módulo."""
        return [d for d in self._dependencies if d.module_id == module_id]
    
    async def add_dependency(
        self, 
        module_id: str, 
        depends_on: str, 
        version_min: Optional[str] = None,
        version_max: Optional[str] = None,
        required: bool = True
    ) -> bool:
        """Adiciona dependência entre módulos."""
        dep = ModuleDependency(
            module_id=module_id,
            depends_on=depends_on,
            version_min=version_min,
            version_max=version_max,
            required=required
        )
        self._dependencies.append(dep)
        return True
    
    # ---------- HEALTH TRACKING ---------- 
    async def record_health_check(self, module_id: str, health) -> None:
        """Registra resultado de health check (mock - só loga)."""
        logger.info("health_check.recorded", extra={
            "module_id": module_id,
            "status": health.status,
            "check_type": health.check_type
        })