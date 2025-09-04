#!/usr/bin/env python3
"""
Script para criar schema de registry de módulos no PostgreSQL.

Este schema permite:
- Registrar módulos dinamicamente
- Salvar configuração por módulo  
- Tracking de dependências
- Histórico de carregamento
- Estado e health checks

Uso:
    python app/db_schema/create_module_schema.py
    python app/db_schema/create_module_schema.py --drop-existing
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.controllers.db_controller import get_conn
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# =========================
#   SQL SCHEMAS
# =========================

MODULES_TABLE = """
CREATE TABLE IF NOT EXISTS modules (
    id                TEXT PRIMARY KEY,                           -- auth, users, agents
    name              TEXT NOT NULL,                              -- "Sistema de Autenticação"
    kind              TEXT NOT NULL CHECK (kind IN ('system','admin','optional')),
    version           TEXT NOT NULL,                              -- 1.0.0, 2.1.3
    status            TEXT NOT NULL CHECK (status IN ('active','disabled','error','installing')),
    
    -- UI e apresentação
    display_order     INTEGER DEFAULT 1000,                      -- ordem na UI
    description       TEXT,                                       -- descrição longa
    author            TEXT,                                       -- quem criou
    icon              TEXT,                                       -- ícone padrão
    
    -- Configuração e manifesto
    manifest          JSONB NOT NULL,                            -- manifesto completo do módulo
    config            JSONB DEFAULT '{}',                        -- configurações específicas
    
    -- Estado e performance
    installed_at      TIMESTAMPTZ DEFAULT NOW(),
    last_loaded_at    TIMESTAMPTZ,                              -- última vez que carregou
    last_error_at     TIMESTAMPTZ,                              -- último erro
    error_message     TEXT,                                      -- mensagem do último erro
    load_count        INTEGER DEFAULT 0,                         -- quantas vezes carregou
    
    -- Auditoria
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
"""

MODULE_DEPENDENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS module_dependencies (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    depends_on      TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    version_min     TEXT,                                        -- versão mínima requerida
    version_max     TEXT,                                        -- versão máxima suportada
    required        BOOLEAN DEFAULT true,                        -- dependência obrigatória?
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(module_id, depends_on)
);
"""

MODULE_SERVICES_TABLE = """
CREATE TABLE IF NOT EXISTS module_services (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    service_name    TEXT NOT NULL,                              -- user_service, auth_service
    service_class   TEXT NOT NULL,                              -- UserService, AuthService  
    factory_func    TEXT,                                       -- build_user_service_from_settings
    singleton       BOOLEAN DEFAULT true,                       -- reutilizar instância?
    dependencies    TEXT[],                                     -- [user_repo, audit_repo]
    status          TEXT DEFAULT 'registered' CHECK (status IN ('registered','active','error')),
    
    -- Estado
    last_created_at TIMESTAMPTZ,                               -- última instanciação
    instance_count  INTEGER DEFAULT 0,                         -- quantas instâncias criadas
    error_message   TEXT,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(module_id, service_name)
);
"""

MODULE_HEALTH_TABLE = """
CREATE TABLE IF NOT EXISTS module_health_checks (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    check_type      TEXT NOT NULL,                              -- startup, periodic, manual
    status          TEXT NOT NULL CHECK (status IN ('healthy','degraded','unhealthy')),
    message         TEXT,
    response_time_ms INTEGER,
    details         JSONB,
    
    checked_at      TIMESTAMPTZ DEFAULT NOW(),
    
    -- Index por módulo + timestamp para queries de histórico
    UNIQUE(module_id, checked_at)
);
"""

INDEXES = """
-- Módulos
CREATE INDEX IF NOT EXISTS idx_modules_status ON modules(status);
CREATE INDEX IF NOT EXISTS idx_modules_kind ON modules(kind);
CREATE INDEX IF NOT EXISTS idx_modules_display_order ON modules(display_order);
CREATE INDEX IF NOT EXISTS idx_modules_last_loaded ON modules(last_loaded_at);

-- Dependências  
CREATE INDEX IF NOT EXISTS idx_deps_module_id ON module_dependencies(module_id);
CREATE INDEX IF NOT EXISTS idx_deps_depends_on ON module_dependencies(depends_on);

-- Services
CREATE INDEX IF NOT EXISTS idx_services_module_id ON module_services(module_id);
CREATE INDEX IF NOT EXISTS idx_services_status ON module_services(status);

-- Health checks
CREATE INDEX IF NOT EXISTS idx_health_module_id ON module_health_checks(module_id);
CREATE INDEX IF NOT EXISTS idx_health_checked_at ON module_health_checks(checked_at);

-- Partial index para módulos ativos (performance)
CREATE INDEX IF NOT EXISTS idx_modules_active ON modules(id, display_order) WHERE status = 'active';
"""

SAMPLE_DATA = """
-- Módulos existentes do sistema
INSERT INTO modules (id, name, kind, version, status, display_order, description, manifest, config) VALUES 
(
    'auth',
    'Sistema de Autenticação',
    'system', 
    '1.0.0',
    'active',
    100,
    'Autenticação JWT, sessões, reset de senha, API keys',
    '{
        "id": "auth",
        "name": "Sistema de Autenticação",
        "kind": "system",
        "version": "1.0.0", 
        "order": 100,
        "buttons": [],
        "apis": [
            {
                "id": "main",
                "baseUrl": "/v1/auth",
                "auth": "none",
                "allowedPaths": ["*"],
                "timeoutMs": 5000,
                "rateLimit": {"maxRps": 10}
            }
        ],
        "permissions": ["net:request"]
    }',
    '{
        "access_ttl_sec": 900,
        "refresh_ttl_sec": 86400,
        "rate_limit_per_ip": 5,
        "enable_password_reset": true,
        "jwt_algorithm": "RS256"
    }'
),
(
    'users', 
    'Gestão de Usuários',
    'system',
    '1.0.0',
    'active', 
    200,
    'CRUD de usuários, perfis, preferências',
    '{
        "id": "users",
        "name": "Gestão de Usuários", 
        "kind": "system",
        "version": "1.0.0",
        "order": 200,
        "buttons": [
            {
                "id": "my_profile",
                "label": "Meu Perfil",
                "route": "/profile",
                "icon": "account",
                "order": 1
            }
        ],
        "apis": [
            {
                "id": "main", 
                "baseUrl": "/v1/users",
                "auth": "core",
                "allowedPaths": ["*"],
                "timeoutMs": 5000
            }
        ],
        "permissions": ["net:request"]
    }',
    '{
        "password_min_length": 8,
        "max_users_per_tenant": 1000,
        "enable_self_registration": false,
        "default_modules": ["auth", "workspace"]
    }'
),
(
    'agents',
    'Agentes de IA',
    'optional',
    '0.9.0', 
    'active',
    300,
    'Conversas com agentes especializados, geração de código',
    '{
        "id": "agents",
        "name": "Agentes de IA",
        "kind": "optional", 
        "version": "0.9.0",
        "order": 300,
        "buttons": [
            {
                "id": "chat",
                "label": "Chat IA", 
                "route": "/chat",
                "icon": "robot",
                "order": 1
            }
        ],
        "apis": [
            {
                "id": "main",
                "baseUrl": "/v1/agents", 
                "auth": "core",
                "allowedPaths": ["*"],
                "timeoutMs": 30000,
                "rateLimit": {"maxRps": 2}
            }
        ],
        "permissions": ["net:request", "net:stream"]
    }',
    '{
        "openai_model": "gpt-4",
        "max_context_tokens": 8000,
        "rate_limit_per_user": 20,
        "enable_code_execution": true,
        "default_agent": "code_gen"
    }'
) ON CONFLICT (id) DO NOTHING;

-- Dependências
INSERT INTO module_dependencies (module_id, depends_on, required) VALUES 
('users', 'auth', true),
('agents', 'auth', true),
('agents', 'users', false)  -- optional: pode funcionar sem users
ON CONFLICT (module_id, depends_on) DO NOTHING;

-- Services registrados 
INSERT INTO module_services (module_id, service_name, service_class, factory_func, dependencies) VALUES
('auth', 'auth_service', 'AuthService', 'build_auth_service_from_settings', '{"user_repo","refresh_repo","audit_repo"}'),
('users', 'user_service', 'UserService', 'build_user_service_from_settings', '{"user_repo","audit_repo"}'), 
('agents', 'agent_service', 'AgentService', 'build_agent_service_from_settings', '{"openai_client","conversation_repo"}')
ON CONFLICT (module_id, service_name) DO NOTHING;
"""

DROP_TABLES = """
DROP TABLE IF EXISTS module_health_checks CASCADE;
DROP TABLE IF EXISTS module_services CASCADE;
DROP TABLE IF EXISTS module_dependencies CASCADE; 
DROP TABLE IF EXISTS modules CASCADE;
"""


async def create_schema(drop_existing: bool = False):
    """Cria schema de módulos no PostgreSQL."""
    
    logger.info("[module_schema] Criando schema de módulos...")
    
    try:
        async with get_conn() as conn:
            
            if drop_existing:
                logger.warning("[module_schema] Removendo tabelas existentes...")
                await conn.execute(DROP_TABLES)
            
            # Criar tabelas
            logger.info("[module_schema] Criando tabela 'modules'...")
            await conn.execute(MODULES_TABLE)
            
            logger.info("[module_schema] Criando tabela 'module_dependencies'...")
            await conn.execute(MODULE_DEPENDENCIES_TABLE)
            
            logger.info("[module_schema] Criando tabela 'module_services'...")
            await conn.execute(MODULE_SERVICES_TABLE)
            
            logger.info("[module_schema] Criando tabela 'module_health_checks'...")
            await conn.execute(MODULE_HEALTH_TABLE)
            
            # Criar índices
            logger.info("[module_schema] Criando índices...")
            await conn.execute(INDEXES)
            
            # Inserir dados iniciais
            logger.info("[module_schema] Inserindo dados iniciais...")
            await conn.execute(SAMPLE_DATA)
            
            logger.info("[module_schema] ✅ Schema criado com sucesso!")
            
    except Exception as e:
        logger.error(f"[module_schema] ❌ Erro criando schema: {e}")
        raise


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Cria schema de registry de módulos")
    parser.add_argument("--drop-existing", action="store_true", help="Remove tabelas existentes antes de criar")
    
    args = parser.parse_args()
    
    try:
        await create_schema(drop_existing=args.drop_existing)
        
        print("\\n🎉 Schema de módulos criado!")
        print("\\n📋 Próximos passos:")
        print("1. Implementar ModuleRegistry service")
        print("2. Implementar ServiceContainer")  
        print("3. Migrar módulos existentes para novo sistema")
        print("4. Implementar Admin APIs")
        print("\\n🔍 Verificar dados:")
        print("   SELECT id, name, status FROM modules ORDER BY display_order;")
        
    except Exception as e:
        logger.error(f"Falha criando schema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())