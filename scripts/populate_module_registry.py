#!/usr/bin/env python3
"""
Script para popular o module registry com módulos existentes do sistema.

Este script:
- Analisa módulos existentes em app/api/
- Gera manifestos baseados na estrutura atual  
- Registra no banco de dados
- Configura dependências básicas

Uso:
    python scripts/populate_module_registry.py
    python scripts/populate_module_registry.py --dry-run  # só mostra o que faria
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.services.module_registry_service import ModuleRegistryService, PgModuleRepo
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# =========================
#   DEFINIÇÕES DOS MÓDULOS EXISTENTES
# =========================
EXISTING_MODULES = {
    "auth": {
        "manifest": {
            "id": "auth",
            "name": "Sistema de Autenticação",
            "kind": "system",
            "version": "1.0.0",
            "order": 100,
            "description": "Autenticação JWT, sessões, reset de senha, validação API keys",
            "author": "Sistema",
            "buttons": [],
            "apis": [
                {
                    "id": "main",
                    "baseUrl": "/v1/auth", 
                    "auth": "none",
                    "allowedPaths": ["*"],
                    "timeoutMs": 10000,
                    "rateLimit": {"maxRps": 10}
                }
            ],
            "permissions": ["net:request"]
        },
        "config": {
            "access_ttl_sec": 900,
            "refresh_ttl_sec": 86400,
            "rate_limit_login_per_ip": 5,
            "enable_password_reset": True,
            "jwt_algorithm": "RS256",
            "cookie_secure": True,
            "cookie_httponly": True
        },
        "dependencies": []
    },
    
    "users": {
        "manifest": {
            "id": "users", 
            "name": "Gestão de Usuários",
            "kind": "system",
            "version": "1.0.0", 
            "order": 200,
            "description": "CRUD de usuários, perfis, preferências, gestão de permissões",
            "author": "Sistema",
            "buttons": [
                {
                    "id": "my_profile",
                    "label": "Meu Perfil", 
                    "route": "/profile",
                    "icon": "account",
                    "order": 1
                },
                {
                    "id": "users_admin", 
                    "label": "Usuários",
                    "route": "/admin/users",
                    "icon": "people",
                    "order": 2
                }
            ],
            "apis": [
                {
                    "id": "main",
                    "baseUrl": "/v1/users",
                    "auth": "core", 
                    "allowedPaths": ["*"],
                    "timeoutMs": 5000,
                    "rateLimit": {"maxRps": 50}
                }
            ],
            "permissions": ["net:request"]
        },
        "config": {
            "password_min_length": 8,
            "max_users_per_tenant": 1000,
            "enable_self_registration": False,
            "default_modules": ["auth", "workspace"],
            "profile_fields_required": ["nome", "email"],
            "enable_whatsapp": True
        },
        "dependencies": [
            {"module": "auth", "required": True}
        ]
    },
    
    "agents": {
        "manifest": {
            "id": "agents",
            "name": "Agentes de IA", 
            "kind": "optional",
            "version": "0.9.0",
            "order": 300,
            "description": "Conversas com agentes especializados, geração de código, reviews automáticos",
            "author": "Sistema",
            "buttons": [
                {
                    "id": "chat_ai",
                    "label": "Chat IA",
                    "route": "/agents/chat", 
                    "icon": "robot",
                    "order": 1
                },
                {
                    "id": "code_gen",
                    "label": "Gerar Código",
                    "route": "/agents/generate",
                    "icon": "code", 
                    "order": 2
                }
            ],
            "apis": [
                {
                    "id": "main",
                    "baseUrl": "/v1/agents",
                    "auth": "core",
                    "allowedPaths": ["*"],
                    "timeoutMs": 60000,  # IA pode demorar
                    "rateLimit": {"maxRps": 2}  # IA é cara
                }
            ],
            "permissions": ["net:request", "net:stream"]
        },
        "config": {
            "openai_model": "gpt-4",
            "max_context_tokens": 8000,
            "rate_limit_per_user": 20,
            "enable_code_execution": True,
            "default_agent": "code_gen",
            "agents_enabled": ["code_gen", "code_review", "test_gen", "debugger"],
            "streaming_enabled": True
        },
        "dependencies": [
            {"module": "auth", "required": True},
            {"module": "users", "required": False}  # opcional: funciona sem
        ]
    },
    
    "workspace": {
        "manifest": {
            "id": "workspace",
            "name": "Gestão de Workspace",
            "kind": "admin",
            "version": "0.8.0",
            "order": 400,
            "description": "Gestão de projetos, arquivos, versionamento",
            "author": "Sistema", 
            "buttons": [
                {
                    "id": "projects",
                    "label": "Projetos",
                    "route": "/workspace/projects",
                    "icon": "folder",
                    "order": 1
                },
                {
                    "id": "files",
                    "label": "Arquivos", 
                    "route": "/workspace/files",
                    "icon": "file",
                    "order": 2
                }
            ],
            "apis": [
                {
                    "id": "main",
                    "baseUrl": "/v1/workspace",
                    "auth": "core",
                    "allowedPaths": ["*"], 
                    "timeoutMs": 10000
                }
            ],
            "permissions": ["net:request", "net:upload"]
        },
        "config": {
            "max_projects_per_user": 10,
            "max_file_size_mb": 50,
            "enable_git_integration": True,
            "auto_backup": True,
            "backup_interval_hours": 24
        },
        "dependencies": [
            {"module": "auth", "required": True},
            {"module": "users", "required": True}
        ]
    }
}


async def populate_registry(dry_run: bool = False):
    """Popular registry com módulos existentes."""
    
    logger.info("populate_registry.start", extra={"dry_run": dry_run})
    
    if dry_run:
        print("🔍 DRY RUN - Mostrando o que seria feito:\\n")
    
    registry = ModuleRegistryService(PgModuleRepo())
    registered_count = 0
    
    for module_id, module_data in EXISTING_MODULES.items():
        try:
            if dry_run:
                print(f"📦 {module_id}:")
                print(f"   Nome: {module_data['manifest']['name']}")
                print(f"   Tipo: {module_data['manifest']['kind']}")
                print(f"   Versão: {module_data['manifest']['version']}")
                print(f"   Dependências: {[d['module'] for d in module_data['dependencies']]}")
                print(f"   APIs: {len(module_data['manifest'].get('apis', []))}")
                print(f"   Botões: {len(module_data['manifest'].get('buttons', []))}")
                print()
                continue
            
            # Verificar se já existe
            existing = await registry.get_module(module_id)
            if existing:
                print(f"⚠️  Módulo '{module_id}' já registrado (pulando)")
                continue
            
            # Registrar módulo
            module_info = await registry.register_module(
                manifest=module_data["manifest"],
                config=module_data["config"]
            )
            
            print(f"✅ Registrado: {module_id} - {module_info.name}")
            registered_count += 1
            
        except Exception as e:
            print(f"❌ Erro registrando {module_id}: {e}")
            logger.error("populate.module_failed", extra={"module_id": module_id, "error": str(e)})
    
    if not dry_run:
        print(f"\\n🎉 Registry populado!")
        print(f"   Módulos registrados: {registered_count}")
        print(f"   Total no sistema: {len(EXISTING_MODULES)}")
        
        # Mostrar resumo
        print("\\n📊 Resumo dos módulos:")
        modules = await registry.list_modules()
        for module in modules:
            deps = await registry.get_dependencies(module.id)
            dep_names = [d.depends_on for d in deps]
            print(f"   {module.id:12} | {module.status:8} | deps: {dep_names}")
        
        print("\\n📋 Próximos passos:")
        print("1. Implementar ServiceContainer integration")
        print("2. Migrar routes.py para usar container DI")
        print("3. Criar Admin APIs para gerenciar módulos")
        print("4. Implementar hot-reload de configurações")


async def analyze_filesystem_modules():
    """Analisa módulos existentes no filesystem."""
    
    print("🔍 Analisando módulos no filesystem:\\n")
    
    api_path = Path("app/app/api")
    if not api_path.exists():
        print("❌ Diretório app/app/api não encontrado")
        return
    
    discovered = []
    
    for module_dir in api_path.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue
            
        routes_file = module_dir / "routes.py"
        schemas_file = module_dir / "schemas.py"
        
        module_info = {
            "id": module_dir.name,
            "has_routes": routes_file.exists(),
            "has_schemas": schemas_file.exists(),
            "in_registry": module_dir.name in EXISTING_MODULES
        }
        
        # Analisar routes.py se existe
        if routes_file.exists():
            content = routes_file.read_text()
            module_info.update({
                "has_router": "router = APIRouter" in content,
                "has_prefix": f'prefix="/v1/{module_dir.name}"' in content,
                "imports_auth": "from app.api.auth.dependencies" in content
            })
        
        discovered.append(module_info)
        
        # Display
        status = "✅ Registrado" if module_info["in_registry"] else "❓ Não registrado"
        routes = "✅" if module_info["has_routes"] else "❌"
        schemas = "✅" if module_info["has_schemas"] else "❌"
        
        print(f"{module_dir.name:12} | {status:13} | routes: {routes} | schemas: {schemas}")
    
    # Módulos não registrados
    unregistered = [m for m in discovered if not m["in_registry"]]
    if unregistered:
        print(f"\\n⚠️  Módulos não registrados encontrados: {len(unregistered)}")
        for m in unregistered:
            print(f"   - {m['id']}")
        print("\\n💡 Adicione-os em EXISTING_MODULES para incluir no registry")
    
    return discovered


def show_registry_schema():
    """Mostra estrutura do schema de registry."""
    
    print("🗄️  Schema do Module Registry:\\n")
    
    tables = {
        "modules": [
            "id (PK)", "name", "kind", "version", "status",
            "display_order", "description", "manifest (JSON)", "config (JSON)",
            "installed_at", "last_loaded_at", "error_message", "load_count"
        ],
        "module_dependencies": [
            "module_id → modules(id)", "depends_on → modules(id)", 
            "version_min", "required"
        ],
        "module_services": [
            "module_id", "service_name", "service_class",
            "singleton", "dependencies[]", "status"
        ],
        "module_health_checks": [
            "module_id", "check_type", "status", "message",
            "response_time_ms", "details (JSON)", "checked_at"
        ]
    }
    
    for table_name, columns in tables.items():
        print(f"📋 {table_name}:")
        for col in columns:
            print(f"   - {col}")
        print()


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Popular module registry com módulos existentes")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria feito")
    parser.add_argument("--analyze", action="store_true", help="Analisa módulos no filesystem")
    parser.add_argument("--schema", action="store_true", help="Mostra schema do registry")
    
    args = parser.parse_args()
    
    if args.schema:
        show_registry_schema()
        return
    
    if args.analyze:
        await analyze_filesystem_modules()
        return
    
    try:
        await populate_registry(dry_run=args.dry_run)
        
        if not args.dry_run:
            print("\\n✅ Registry populado com sucesso!")
            print("\\n🔍 Verificar dados:")
            print("   SELECT id, name, status, kind FROM modules ORDER BY display_order;")
            print("   SELECT module_id, depends_on FROM module_dependencies;")
            
    except Exception as e:
        logger.error(f"Falha populando registry: {e}")
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())