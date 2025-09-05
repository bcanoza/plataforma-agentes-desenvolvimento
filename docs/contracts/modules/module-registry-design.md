# 🏗️ Design do Sistema de Registry de Módulos

Este documento propõe como **salvar, administrar e gerenciar** módulos, controllers e services no sistema.

## 🚨 **Situação Atual (Problemática)**

### **Controllers/Routes:**
```python
# app/core/api_loader.py - Discovery por filesystem
_loaded_modules: set[str] = set()  # ← Em memória, perdido no restart

# app/api/users/routes.py - Service instanciado ad-hoc  
service = build_user_service_from_settings()  # ← Nova instância toda request
```

### **Services:**
```python
# app/api/auth/routes.py
auth_service = build_auth_service_from_settings()  # ← Instância global

# app/api/users/routes.py  
service = UserService()  # ← Instância diferente
```

**Problemas identificados:**
- ❌ **Sem persistência** - módulos são descobertos por filesystem a cada startup
- ❌ **Inconsistência** - alguns services são globais, outros locais
- ❌ **Sem administração central** - não há APIs para gerenciar módulos
- ❌ **Configuração hardcoded** - settings estáticos, não dinâmicos
- ❌ **Memory leaks** - services podem não ser limpos adequadamente

---

## ✅ **Proposta: Sistema de Registry Estruturado**

### **1. Module Registry (Persistido)**

**Tabela de módulos:**
```sql
CREATE TABLE modules (
    id                TEXT PRIMARY KEY,           -- auth, users, agents
    name              TEXT NOT NULL,              -- "Sistema de Autenticação" 
    kind              TEXT NOT NULL,              -- system, admin, optional
    version           TEXT NOT NULL,              -- 1.0.0
    status            TEXT NOT NULL,              -- active, disabled, error
    
    -- Metadata
    display_order     INTEGER DEFAULT 1000,
    description       TEXT,
    author            TEXT,
    
    -- Configuração
    manifest          JSONB NOT NULL,            -- JSON completo do manifesto
    config            JSONB,                     -- Configurações específicas
    
    -- Estado
    installed_at      TIMESTAMPTZ DEFAULT NOW(),
    last_loaded_at    TIMESTAMPTZ,
    error_message     TEXT,
    load_count        INTEGER DEFAULT 0,
    
    -- Auditoria
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_modules_status ON modules(status);
CREATE INDEX idx_modules_kind ON modules(kind);
```

**Tabela de dependências:**
```sql
CREATE TABLE module_dependencies (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id),
    depends_on      TEXT NOT NULL REFERENCES modules(id),
    version_min     TEXT,
    version_max     TEXT,
    required        BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(module_id, depends_on)
);
```

### **2. Service Container (Centralizado)**

**Container de DI Global:**
```python
# app/core/service_container.py

from typing import Dict, Type, Any, Optional, TypeVar, Callable
from dataclasses import dataclass
import asyncio

T = TypeVar('T')

@dataclass
class ServiceDefinition:
    """Definição de como criar um service."""
    service_class: Type
    factory_func: Callable[[], Any]
    singleton: bool = True
    dependencies: List[str] = None
    lifecycle: str = "application"  # application, request, module

class ServiceContainer:
    """Container centralizado de dependency injection."""
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._module_services: Dict[str, List[str]] = {}  # módulo -> [services]
    
    def register(
        self, 
        name: str, 
        service_class: Type[T], 
        factory_func: Callable[[], T],
        *,
        module_id: str,
        singleton: bool = True,
        dependencies: List[str] = None
    ):
        """Registra um service no container."""
        self._services[name] = ServiceDefinition(
            service_class=service_class,
            factory_func=factory_func,
            singleton=singleton,
            dependencies=dependencies or [],
        )
        
        # Associar ao módulo
        if module_id not in self._module_services:
            self._module_services[module_id] = []
        self._module_services[module_id].append(name)
    
    async def get(self, name: str) -> Any:
        """Obtém instância do service."""
        if name not in self._services:
            raise ValueError(f"Service '{name}' não registrado")
        
        definition = self._services[name]
        
        # Singleton: reutilizar instância
        if definition.singleton and name in self._instances:
            return self._instances[name]
        
        # Resolver dependências
        kwargs = {}
        for dep_name in definition.dependencies:
            kwargs[dep_name] = await self.get(dep_name)
        
        # Criar instância
        if asyncio.iscoroutinefunction(definition.factory_func):
            instance = await definition.factory_func(**kwargs)
        else:
            instance = definition.factory_func(**kwargs)
        
        # Cachear se singleton
        if definition.singleton:
            self._instances[name] = instance
            
        return instance
    
    async def unload_module_services(self, module_id: str):
        """Remove services de um módulo específico."""
        if module_id not in self._module_services:
            return
        
        for service_name in self._module_services[module_id]:
            # Cleanup de instâncias
            if service_name in self._instances:
                instance = self._instances[service_name]
                if hasattr(instance, 'cleanup'):
                    await instance.cleanup()
                del self._instances[service_name]
            
            # Remove definição
            if service_name in self._services:
                del self._services[service_name]
        
        del self._module_services[module_id]

# Container global
container = ServiceContainer()
```

### **3. Module Manager (Administração)**

**Service para gerenciar módulos:**
```python
# app/services/module_manager_service.py

@dataclass
class ModuleInfo:
    """Informações de um módulo."""
    id: str
    name: str
    kind: str
    version: str
    status: str
    manifest: dict
    config: Optional[dict]
    installed_at: str
    last_loaded_at: Optional[str]
    error_message: Optional[str]

class ModuleManagerService:
    """Service para administrar módulos."""
    
    def __init__(self, module_repo: ModuleRepo, container: ServiceContainer):
        self.repo = module_repo
        self.container = container
    
    async def list_modules(self) -> List[ModuleInfo]:
        """Lista todos os módulos registrados."""
        return await self.repo.find_all()
    
    async def register_module(self, manifest: dict, config: Optional[dict] = None) -> ModuleInfo:
        """Registra novo módulo no registry."""
        module_id = manifest["id"]
        
        # Validar manifesto
        self._validate_manifest(manifest)
        
        # Verificar dependências
        await self._check_dependencies(manifest.get("dependencies", []))
        
        # Salvar no BD
        module = await self.repo.insert_module(
            id=module_id,
            name=manifest["name"],
            kind=manifest["kind"], 
            version=manifest["version"],
            status="registered",
            manifest=manifest,
            config=config,
        )
        
        logger.info("module.registered", extra={"module_id": module_id})
        return module
    
    async def enable_module(self, module_id: str) -> bool:
        """Ativa um módulo (carrega services e routes)."""
        module = await self.repo.find_by_id(module_id)
        if not module:
            raise ModuleError("ERR_MODULE_NOT_FOUND", f"Módulo {module_id} não encontrado")
        
        try:
            # 1. Registrar services no container
            await self._register_module_services(module)
            
            # 2. Carregar routes no FastAPI  
            await self._load_module_routes(module)
            
            # 3. Atualizar status
            await self.repo.update_module(
                module_id,
                status="active",
                last_loaded_at=datetime.utcnow().isoformat(),
                error_message=None
            )
            
            logger.info("module.enabled", extra={"module_id": module_id})
            return True
            
        except Exception as e:
            # Salvar erro
            await self.repo.update_module(
                module_id,
                status="error", 
                error_message=str(e)
            )
            logger.error("module.enable_failed", extra={"module_id": module_id, "error": str(e)})
            raise
    
    async def disable_module(self, module_id: str) -> bool:
        """Desativa um módulo (remove services e routes)."""
        try:
            # 1. Unload services
            await self.container.unload_module_services(module_id)
            
            # 2. Remove routes (mais complexo, precisa restart do FastAPI)
            # Por enquanto, apenas marcar como disabled
            
            # 3. Atualizar status
            await self.repo.update_module(module_id, status="disabled")
            
            logger.info("module.disabled", extra={"module_id": module_id})
            return True
            
        except Exception as e:
            logger.error("module.disable_failed", extra={"module_id": module_id, "error": str(e)})
            return False
```

### **4. API de Administração de Módulos**

**Endpoints para gerenciar módulos:**
```python
# app/api/admin/modules_routes.py

router = APIRouter(prefix="/v1/admin/modules", tags=["Module Administration"])
module_manager = build_module_manager_from_settings()

@router.get("/", response_model=List[ModuleInfo])
async def list_modules(current: CurrentUser = Depends(require_admin)):
    """Lista todos os módulos do sistema."""
    return await module_manager.list_modules()

@router.get("/{module_id}", response_model=ModuleInfo)
async def get_module(module_id: str, current: CurrentUser = Depends(require_admin)):
    """Detalhes de um módulo específico."""
    module = await module_manager.get_module(module_id)
    if not module:
        raise HTTPException(404, detail="Módulo não encontrado")
    return module

@router.post("/register", response_model=ModuleInfo, status_code=201)
async def register_module(
    manifest: dict = Body(...),
    config: Optional[dict] = Body(None),
    current: CurrentUser = Depends(require_admin)
):
    """Registra novo módulo no sistema."""
    return await module_manager.register_module(manifest, config)

@router.post("/{module_id}/enable", status_code=204)
async def enable_module(module_id: str, current: CurrentUser = Depends(require_admin)):
    """Ativa um módulo."""
    ok = await module_manager.enable_module(module_id)
    if not ok:
        raise HTTPException(400, detail="Falha ao ativar módulo")

@router.post("/{module_id}/disable", status_code=204) 
async def disable_module(module_id: str, current: CurrentUser = Depends(require_admin)):
    """Desativa um módulo."""
    ok = await module_manager.disable_module(module_id)
    if not ok:
        raise HTTPException(400, detail="Falha ao desativar módulo")

@router.put("/{module_id}/config")
async def update_module_config(
    module_id: str,
    config: dict,
    current: CurrentUser = Depends(require_admin)
):
    """Atualiza configuração de um módulo."""
    return await module_manager.update_config(module_id, config)

@router.get("/{module_id}/health")
async def module_health(module_id: str, current: CurrentUser = Depends(require_admin)):
    """Health check específico do módulo."""
    return await module_manager.check_module_health(module_id)
```

---

## 🔄 **Evolução do Sistema Atual**

### **Problema 1: Services Inconsistentes**

**Atual:**
```python
# app/api/auth/routes.py  
auth_service = build_auth_service_from_settings()  # ← Global

# app/api/users/routes.py
service = UserService()  # ← Local, nova instância
```

**Proposta:**
```python
# app/core/module_loader.py - Novo loader com registry

class ModuleLoader:
    def __init__(self, registry: ModuleRegistry, container: ServiceContainer):
        self.registry = registry
        self.container = container
    
    async def load_module(self, module_id: str) -> bool:
        """Carrega módulo completo (services + routes)."""
        module_info = await self.registry.get_module(module_id)
        
        # 1. Registrar services no container
        await self._register_services(module_info)
        
        # 2. Carregar routes
        router = await self._load_routes(module_info)
        
        # 3. Registrar no FastAPI
        app.include_router(router)
        
        return True
    
    async def _register_services(self, module_info: ModuleInfo):
        """Registra services do módulo no container."""
        
        # Services padrão baseados no módulo
        if module_info.id == "auth":
            self.container.register(
                "auth_service",
                AuthService,
                build_auth_service_from_settings,
                module_id="auth",
                singleton=True
            )
        elif module_info.id == "users":
            self.container.register(
                "user_service", 
                UserService,
                lambda: UserService(
                    user_repo=self.container.get("user_repo"),
                    audit_repo=self.container.get("audit_repo")
                ),
                module_id="users",
                dependencies=["user_repo", "audit_repo"]
            )
```

### **Problema 2: Configuração Hardcoded**

**Atual:**
```python
# Configuração misturada no código
JWT_SECRET = settings.JWT_SECRET
REFRESH_TTL_SEC = settings.REFRESH_TTL_SEC
```

**Proposta - Configuração Dinâmica:**
```python
# Config salva por módulo no BD
{
  "auth": {
    "jwt_secret": "***",
    "access_ttl_sec": 900,
    "refresh_ttl_sec": 86400,
    "rate_limit_per_ip": 5,
    "enable_2fa": false
  },
  "users": {
    "password_min_length": 8,
    "max_users": 1000,
    "enable_self_registration": false,
    "default_modules": ["auth", "workspace"]
  }
}

# Services recebem config do registry
class AuthService:
    def __init__(self, config: dict, user_repo: UserRepo, ...):
        self.config = config
        self.access_ttl = config.get("access_ttl_sec", 900)
        # ...
```

### **Problema 3: Sem Administração Central**

**Proposta - Admin APIs:**
```python
# Gerenciar módulos via API REST
POST /v1/admin/modules/register     # Instalar novo módulo
PUT  /v1/admin/modules/{id}/enable  # Ativar módulo
PUT  /v1/admin/modules/{id}/disable # Desativar módulo
PUT  /v1/admin/modules/{id}/config  # Atualizar configuração
GET  /v1/admin/modules/{id}/health  # Status do módulo
GET  /v1/admin/modules/{id}/logs    # Logs específicos
```

---

## 🎯 **Arquitetura Proposta**

### **Startup Flow:**
```python
# app/main.py - Startup melhorado

async def startup():
    # 1. Inicializar container de services
    await container.initialize()
    
    # 2. Carregar módulos do registry
    registry = ModuleRegistry()
    loader = ModuleLoader(registry, container)
    
    active_modules = await registry.get_active_modules()
    for module_info in active_modules:
        try:
            await loader.load_module(module_info.id)
            logger.info("module.loaded", extra={"module_id": module_info.id})
        except Exception as e:
            logger.error("module.load_failed", extra={"module_id": module_info.id, "error": str(e)})
            await registry.mark_module_error(module_info.id, str(e))
```

### **Dependency Injection Pattern:**
```python
# Novo padrão para routes.py

# app/api/users/routes.py  
router = APIRouter(prefix="/v1/users", tags=["Users"])

# Service injetado pelo container (não instanciado localmente)
async def get_user_service() -> UserService:
    """Dependency que obtém service do container."""
    return await container.get("user_service")

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current: CurrentUser = Depends(require_admin),
    service: UserService = Depends(get_user_service)  # ← Injetado pelo container
):
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail="Usuário não encontrado")
    return build_user_response(user)
```

### **Module Configuration:**
```python
# app/core/module_config.py

class ModuleConfig:
    """Configuração dinâmica por módulo."""
    
    def __init__(self, registry: ModuleRegistry):
        self.registry = registry
        self._cache: Dict[str, dict] = {}
    
    async def get_config(self, module_id: str) -> dict:
        """Obtém configuração de um módulo."""
        if module_id not in self._cache:
            module = await self.registry.get_module(module_id)
            self._cache[module_id] = module.config or {}
        return self._cache[module_id]
    
    async def update_config(self, module_id: str, config: dict):
        """Atualiza configuração e invalida cache."""
        await self.registry.update_module_config(module_id, config)
        if module_id in self._cache:
            del self._cache[module_id]

# Usage nos services
class AuthService:
    def __init__(self, module_config: ModuleConfig, user_repo: UserRepo, ...):
        self.config = module_config
        self.users = user_repo
        # ...
    
    async def _get_access_ttl(self) -> int:
        config = await self.config.get_config("auth")
        return config.get("access_ttl_sec", 900)
```

---

## 🔄 **Migração do Sistema Atual**

### **Fase 1: Registry Base (sem breaking changes)**
```python
# 1. Criar tabelas de módulos
python app/db_schema/create_module_schema.py

# 2. Popular registry com módulos existentes  
python scripts/populate_module_registry.py

# 3. Manter loader atual funcionando
# (backward compatibility)
```

### **Fase 2: Service Container**
```python
# 1. Implementar container
# 2. Migrar services um por vez para uso do container
# 3. Manter wiring atual como fallback
```

### **Fase 3: Admin APIs**  
```python
# 1. Implementar APIs de administração
# 2. UI para gerenciar módulos
# 3. Hot-reload de módulos sem restart
```

---

## 💾 **Schema de Banco Proposto**

```sql
-- Módulos registrados
CREATE TABLE modules (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    kind              TEXT NOT NULL CHECK (kind IN ('system','admin','optional')),
    version           TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('active','disabled','error','installing')),
    
    display_order     INTEGER DEFAULT 1000,
    description       TEXT,
    author            TEXT,
    
    manifest          JSONB NOT NULL,
    config            JSONB DEFAULT '{}',
    
    installed_at      TIMESTAMPTZ DEFAULT NOW(),
    last_loaded_at    TIMESTAMPTZ,
    error_message     TEXT,
    load_count        INTEGER DEFAULT 0,
    
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Dependências entre módulos
CREATE TABLE module_dependencies (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    depends_on      TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE, 
    version_min     TEXT,
    required        BOOLEAN DEFAULT true,
    
    UNIQUE(module_id, depends_on)
);

-- Services registrados por módulo
CREATE TABLE module_services (
    id              BIGSERIAL PRIMARY KEY,
    module_id       TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    service_name    TEXT NOT NULL,
    service_class   TEXT NOT NULL,
    singleton       BOOLEAN DEFAULT true,
    dependencies    TEXT[],
    status          TEXT DEFAULT 'registered',
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(module_id, service_name)
);
```

---

## 🎯 **Como Aplicar aos Módulos Auth/Users**

### **Registry Entries:**
```json
// Módulo auth
{
  "id": "auth",
  "name": "Sistema de Autenticação", 
  "kind": "system",
  "version": "1.0.0",
  "status": "active",
  "manifest": {
    "buttons": [],
    "apis": [{"id": "main", "baseUrl": "/v1/auth", "auth": "none"}],
    "permissions": ["net:request"]
  },
  "config": {
    "access_ttl_sec": 900,
    "refresh_ttl_sec": 86400,
    "rate_limit_login": 5,
    "enable_password_reset": true
  }
}

// Módulo users  
{
  "id": "users",
  "name": "Gestão de Usuários",
  "kind": "system", 
  "version": "1.0.0",
  "status": "active",
  "dependencies": ["auth"],  // ← Dependência explícita
  "config": {
    "max_users": 1000,
    "password_min_length": 8,
    "enable_self_registration": false
  }
}
```

### **Service Registration:**
```python
# app/core/bootstrap.py - Startup melhorado

async def register_core_modules():
    """Registra módulos do sistema no container."""
    
    # Repositories compartilhados
    container.register(
        "user_repo", PgUserRepo, PgUserRepo,
        module_id="core", singleton=True
    )
    container.register(
        "audit_repo", PgAuditLogRepo, PgAuditLogRepo, 
        module_id="core", singleton=True
    )
    
    # Auth service
    container.register(
        "auth_service", AuthService, build_auth_service_from_settings,
        module_id="auth", singleton=True,
        dependencies=["user_repo", "audit_repo"]
    )
    
    # User service  
    container.register(
        "user_service", UserService, 
        lambda user_repo, audit_repo: UserService(user_repo, audit_repo),
        module_id="users", singleton=True,
        dependencies=["user_repo", "audit_repo"]
    )
```

### **Routes com DI:**
```python
# app/api/users/routes.py - Novo padrão

async def get_user_service() -> UserService:
    """Dependency injection do container."""
    return await container.get("user_service")

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current: CurrentUser = Depends(require_admin),
    service: UserService = Depends(get_user_service)  # ← DI pelo container
):
    user = await service.get_user_by_id(user_id)
    # ...
```

---

## 🚀 **Benefícios da Nova Arquitetura**

### **1. Administração Centralizada**
- ✅ **UI Admin** para ativar/desativar módulos
- ✅ **Configuração dinâmica** sem restart
- ✅ **Health monitoring** por módulo  
- ✅ **Dependency tracking** automático

### **2. Service Management**
- ✅ **Singleton real** - uma instância por service
- ✅ **Lazy loading** - services criados quando necessários
- ✅ **Lifecycle management** - cleanup automático
- ✅ **Hot reloading** - recarregar services em desenvolvimento

### **3. Persistência e Auditoria**
- ✅ **Estado persistido** - módulos sobrevivem restart
- ✅ **Histórico de carregamento** - quando/quantas vezes carregou
- ✅ **Error tracking** - problemas são logados e persistidos
- ✅ **Usage metrics** - quais módulos são mais usados

---

## 📋 **Plano de Implementação**

### **Etapa 1: Registry Foundation**
1. **Criar schema de BD** para módulos
2. **Implementar ModuleRegistry** service 
3. **Popular com módulos existentes**
4. **Manter loader atual funcionando** (compatibilidade)

### **Etapa 2: Service Container**
1. **Implementar ServiceContainer**
2. **Migrar AuthService** para container
3. **Migrar UserService** para container  
4. **Atualizar routes** para usar DI

### **Etapa 3: Admin APIs**
1. **Implementar ModuleManagerService**
2. **Criar endpoints de administração**
3. **UI para gerenciar módulos**
4. **Hot-reload de configurações**

### **Etapa 4: Advanced Features**
1. **Dynamic loading** de módulos externos
2. **Plugin system** para módulos de terceiros
3. **A/B testing** de módulos
4. **Performance monitoring** por módulo

**Quer que eu implemente alguma dessas etapas como exemplo prático?** Posso começar criando o schema do registry e a estrutura base do ServiceContainer! 🚀