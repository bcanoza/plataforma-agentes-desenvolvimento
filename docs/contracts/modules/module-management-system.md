# 🎛️ Sistema de Gestão de Módulos

Este documento responde às questões sobre **como módulos são salvos, administrados e gerenciados** no sistema.

## 🚨 **Problemas da Arquitetura Atual**

### **1. Controllers/Routes Inconsistentes**
```python
# Situação atual problemática:

# app/api/auth/routes.py
auth_service = build_auth_service_from_settings()  # ← Global, singleton

# app/api/users/routes.py  
service = UserService()  # ← Local, nova instância a cada import

# app/controllers/user_controller.py (estrutura antiga)
service = UserService()  # ← Duplicação, inconsistência
```

### **2. Sem Persistência de Estado**
```python
# app/core/api_loader.py
_loaded_modules: set[str] = set()  # ← Em memória, perdido no restart

# Não há registro de:
# - Quais módulos estão ativos
# - Configurações específicas por módulo
# - Histórico de carregamento  
# - Dependências entre módulos
```

### **3. Configuração Hardcoded**
```python
# Configurações espalhadas no código
JWT_SECRET = settings.JWT_SECRET           # ← auth module
REFRESH_TTL = settings.REFRESH_TTL_SEC     # ← auth module
MAX_USERS = settings.MAX_USERS             # ← users module

# Não há como:
# - Alterar configuração sem restart
# - Configuração específica por módulo
# - Persistir configurações customizadas
```

---

## ✅ **Solução Proposta: Sistema de Registry**

### **1. Persistência de Módulos (PostgreSQL)**

**Tabela principal:**
```sql
CREATE TABLE modules (
    id                TEXT PRIMARY KEY,        -- auth, users, agents
    name              TEXT NOT NULL,           -- "Sistema de Autenticação"
    kind              TEXT NOT NULL,           -- system, admin, optional
    version           TEXT NOT NULL,           -- 1.0.0
    status            TEXT NOT NULL,           -- active, disabled, error
    
    -- Apresentação
    display_order     INTEGER DEFAULT 1000,   -- ordem na UI
    description       TEXT,
    author            TEXT,
    
    -- Configuração
    manifest          JSONB NOT NULL,         -- manifesto completo
    config            JSONB DEFAULT '{}',     -- settings específicos
    
    -- Estado
    installed_at      TIMESTAMPTZ DEFAULT NOW(),
    last_loaded_at    TIMESTAMPTZ,           -- última vez carregado
    error_message     TEXT,                  -- último erro
    load_count        INTEGER DEFAULT 0,     -- contador de carregamentos
    
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
```

**Exemplo de dados salvos:**
```json
// Módulo auth
{
  "id": "auth",
  "name": "Sistema de Autenticação",
  "status": "active", 
  "manifest": {
    "apis": [{"baseUrl": "/v1/auth", "auth": "none"}],
    "permissions": ["net:request"]
  },
  "config": {
    "access_ttl_sec": 900,
    "refresh_ttl_sec": 86400,
    "rate_limit_per_ip": 5
  }
}
```

### **2. Service Container (Dependency Injection)**

**Container centralizado:**
```python
# app/core/service_container.py

class ServiceContainer:
    def register(self, name: str, service_class: Type, factory_func: Callable, 
                 *, module_id: str, singleton: bool = True):
        """Registra service no container."""
        
    async def get(self, name: str) -> Any:
        """Obtém instância resolvendo dependências."""
        
    async def unload_module(self, module_id: str) -> int:
        """Remove todos services de um módulo."""

# Instância global
container = ServiceContainer()
```

**Novo padrão nos routes:**
```python
# app/api/users/routes.py (NOVO padrão)

async def get_user_service() -> UserService:
    """Dependency injection do container."""
    return await container.get("user_service")

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service)  # ← DI centralizado
):
    # Service vem do container, com DI automático
```

### **3. Module Registry Service**

**CRUD de módulos:**
```python
# app/services/module_registry_service.py

class ModuleRegistryService:
    async def register_module(self, manifest: dict, config: dict) -> ModuleInfo:
        """Registra novo módulo no sistema."""
        
    async def get_active_modules(self) -> List[ModuleInfo]:
        """Módulos ativos ordenados por dependência."""
        
    async def update_config(self, module_id: str, config: dict) -> bool:
        """Atualiza configuração dinâmica."""
        
    async def set_module_status(self, module_id: str, status: str) -> bool:
        """Ativa/desativa módulo."""
```

---

## 🚀 **Como Funciona na Prática**

### **Startup da Aplicação**
```python
# app/main.py (NOVO)

from app.core.enhanced_module_loader import enhanced_startup_handler

@app.on_event("startup")
async def startup():
    await enhanced_startup_handler(app)

# Fluxo interno:
# 1. Conectar no BD → buscar módulos ativos
# 2. Ordenar por dependências  
# 3. Para cada módulo:
#    a. Registrar services no container
#    b. Carregar routes via import
#    c. Incluir router no FastAPI
#    d. Atualizar status "active" 
#    e. Health check inicial
```

### **Administração via API**
```python
# Gerenciar módulos sem restart:

# Listar módulos
GET /v1/admin/modules/
→ [{"id": "auth", "status": "active", "config": {...}}, ...]

# Ativar módulo  
POST /v1/admin/modules/agents/enable
→ Carrega services + routes dinamicamente

# Atualizar configuração
PUT /v1/admin/modules/auth/config
{"access_ttl_sec": 1800}  # ← Novo TTL
→ Salvo no BD, use /reload para aplicar

# Recarregar módulo
POST /v1/admin/modules/auth/reload  
→ Unload + load com nova config
```

### **Service Resolution**
```python
# Como services são resolvidos:

# 1. Route chama container
service = await container.get("user_service")

# 2. Container verifica dependências
# user_service precisa de: ["user_repo", "audit_repo"]

# 3. Resolve dependências primeiro  
user_repo = await container.get("user_repo")      # ← Singleton
audit_repo = await container.get("audit_repo")    # ← Singleton

# 4. Chama factory com dependências
service = UserService(user_repo=user_repo, audit_repo=audit_repo)

# 5. Cacheia se singleton
container._instances["user_service"] = service

# 6. Retorna instância
return service
```

---

## 🎯 **Resolução dos Problemas**

### **✅ Como módulos são salvos:**
- **BD PostgreSQL** com tabela `modules` 
- **Manifesto JSON** completo por módulo
- **Configuração dinâmica** em campo `config`
- **Estado persistido** (ativo, erro, carregamentos)

### **✅ Como controllers são administrados:**
- **Discovery automático** do registry (não filesystem)
- **Carregamento ordenado** por dependências
- **Hot-reload** sem restart (services)
- **APIs de administração** (`/v1/admin/modules/`)

### **✅ Como services são gerenciados:**
- **Container DI centralizado** - uma instância por service
- **Lifecycle management** - singletons reais, cleanup automático
- **Dependency resolution** - resolve dependências automaticamente
- **Performance tracking** - métricas por service

---

## 📊 **Comparação: Antes vs Depois**

### **Carregamento de Módulos**

**ANTES (atual):**
```python
# app/main.py
include_api_modules(app)
  ↓
# Escaneia app/api/ no filesystem 
for module_dir in filesystem:
    import module.routes
    app.include_router(router)
```

**DEPOIS (proposto):**
```python  
# app/main.py
enhanced_startup_handler(app)
  ↓
# Consulta registry no BD
modules = registry.get_active_modules()
for module in modules:
    container.register_services(module)
    app.include_router(load_routes(module))
```

### **Instanciação de Services**

**ANTES (inconsistente):**
```python
# Alguns globais
auth_service = build_auth_service_from_settings()

# Outros locais  
service = UserService()  # ← Nova instância a cada import
```

**DEPOIS (centralizado):**
```python
# Todos via container
service = await container.get("user_service")  # ← Singleton real

# Com dependency injection automático
user_service ← depende de → user_repo, audit_repo  
container resolve automaticamente
```

### **Configuração**

**ANTES (estática):**
```python
# settings.py
JWT_TTL = 900  # ← Hardcoded, restart para mudar
```

**DEPOIS (dinâmica):**
```python
# BD: modules.config
{"auth": {"access_ttl_sec": 900}}

# API: 
PUT /v1/admin/modules/auth/config {"access_ttl_sec": 1800}
POST /v1/admin/modules/auth/reload  # ← Aplica sem restart
```

---

## 🛠️ **Implementação Prática**

### **Fase 1: Preparar Infrastructure**
```bash
# 1. Criar schema de módulos
python app/db_schema/create_module_schema.py

# 2. Popular com módulos existentes  
python scripts/populate_module_registry.py

# 3. Verificar dados
SELECT id, name, status FROM modules ORDER BY display_order;
```

### **Fase 2: Implementar Container**
```bash
# 1. Implementar ServiceContainer (✅ já feito)
# 2. Migrar auth_service para container
# 3. Migrar user_service para container
# 4. Atualizar routes para usar DI
```

### **Fase 3: Admin APIs**
```bash
# 1. Implementar admin/modules_routes.py (✅ já feito)
# 2. Criar UI para administração  
# 3. Testes das APIs
# 4. Documentação
```

### **Fase 4: Enhanced Loader**
```bash  
# 1. Implementar enhanced_module_loader.py (✅ já feito)
# 2. Integrar no main.py
# 3. Migração gradual do api_loader atual
# 4. Testes de integração
```

---

## 🎯 **Exemplo: Migração do Módulo Auth**

### **Estado Atual:**
```python
# app/api/auth/routes.py
auth_service = build_auth_service_from_settings()  # Global

@router.post("/login")  
async def login(body: LoginRequest):
    bundle = await auth_service.login(...)  # ← Service global
```

### **Após Migração:**
```python
# 1. Service registrado no container (startup)
container.register(
    "auth_service", 
    AuthService,
    build_auth_service_from_settings,
    module_id="auth", 
    singleton=True
)

# 2. Routes usam DI
async def get_auth_service() -> AuthService:
    return await container.get("auth_service")

@router.post("/login")
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)  # ← DI
):
    bundle = await auth_service.login(...)

# 3. Configuração dinâmica
# BD: {"auth": {"access_ttl_sec": 1800}}
# API: PUT /v1/admin/modules/auth/config + reload
```

**Benefícios:**
- ✅ **Service único** - uma instância real de AuthService
- ✅ **Configuração dinâmica** - TTL alterável sem restart
- ✅ **Monitoramento** - health check, metrics, logs
- ✅ **Administração** - ativar/desativar via API

---

## 📋 **APIs de Administração Disponíveis**

### **Gestão de Módulos**
```http
GET    /v1/admin/modules/              # Listar módulos
GET    /v1/admin/modules/{id}          # Detalhes do módulo  
POST   /v1/admin/modules/register     # Registrar novo módulo

POST   /v1/admin/modules/{id}/enable  # Ativar módulo
POST   /v1/admin/modules/{id}/disable # Desativar módulo
POST   /v1/admin/modules/{id}/reload  # Recarregar módulo

GET    /v1/admin/modules/{id}/health  # Health check
GET    /v1/admin/modules/{id}/dependencies # Dependências
```

### **Configuração Dinâmica**
```http  
GET    /v1/admin/modules/{id}/config  # Obter configuração atual
PUT    /v1/admin/modules/{id}/config  # Atualizar configuração

# Exemplo: alterar TTL do auth
PUT /v1/admin/modules/auth/config
{
  "access_ttl_sec": 1800,
  "refresh_ttl_sec": 172800,
  "rate_limit_per_ip": 10
}

POST /v1/admin/modules/auth/reload    # Aplicar mudanças
```

### **Monitoramento**
```http
GET    /v1/admin/modules/stats        # Stats gerais do sistema
GET    /v1/admin/modules/system/container-stats # Stats do DI container  
POST   /v1/admin/modules/system/reload-all      # Recarregar todos (cuidado!)
```

---

## 🔄 **Fluxo Completo: Criação de Novo Módulo**

### **1. Desenvolvimento**
```bash
# Gerar estrutura
python scripts/create_module.py products "Gestão de Produtos" "CRUD produtos e-commerce"

# Implementar lógica específica
# - Editar schemas.py 
# - Implementar ProductService
# - Criar PgProductRepo
# - Escrever testes
```

### **2. Registro no Sistema**
```http
POST /v1/admin/modules/register
{
  "manifest": {
    "id": "products",
    "name": "Gestão de Produtos", 
    "kind": "optional",
    "version": "1.0.0",
    "buttons": [...],
    "apis": [...]
  },
  "config": {
    "max_products": 10000,
    "enable_inventory": true
  }
}
```

### **3. Ativação**
```http
POST /v1/admin/modules/products/enable
→ Registra ProductService no container
→ Carrega routes /v1/products/*  
→ Módulo disponível para uso
```

### **4. Configuração Dinâmica**
```http
# Alterar limites sem restart
PUT /v1/admin/modules/products/config
{"max_products": 50000, "enable_bulk_import": true}

POST /v1/admin/modules/products/reload
→ ProductService recebe nova configuração
```

---

## 🏭 **Service Factory Pattern**

### **Registro de Services**
```python
# app/core/enhanced_module_loader.py

async def _register_user_services(self, module_info: ModuleInfo):
    """Exemplo de como registrar services de um módulo."""
    
    # 1. Ler configuração do módulo
    config = module_info.config
    
    # 2. Registrar dependencies
    self.container.register(
        "user_repo",
        PgUserRepo, 
        lambda: PgUserRepo(pool=get_db_pool()),
        module_id="core",
        singleton=True
    )
    
    # 3. Service principal com configuração
    async def build_user_service(**deps):
        return UserService(
            user_repo=deps["user_repo"],
            audit_repo=deps["audit_repo"],
            config=config  # ← Configuração dinâmica do BD
        )
    
    self.container.register(
        "user_service",
        UserService,
        build_user_service,
        module_id="users",
        singleton=True,
        dependencies=["user_repo", "audit_repo"]
    )
```

### **Usage nos Routes**
```python
# Routes não instanciam services diretamente

async def get_user_service() -> UserService:
    return await container.get("user_service")

# Service injetado automaticamente
@router.get("/{id}")
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service)
):
    # Service já configurado e pronto
    return await service.get_user_by_id(user_id)
```

---

## 🛡️ **Administração e Segurança**

### **Permissões para Administração**
```python
# Apenas super admins podem gerenciar módulos
@router.post("/modules/{id}/enable")
async def enable_module(current: CurrentUser = Depends(require_admin)):
    # Verificar se é super admin
    if "super_admin" not in current.get("roles", []):
        raise HTTPException(403, detail="Super admin required")
```

### **Auditoria de Mudanças**
```python
# Toda mudança é auditada
await audit.write(
    user_id=current["sub"],
    event="module_config_updated",
    metadata={
        "module_id": module_id,
        "old_config": old_config,
        "new_config": new_config
    }
)
```

### **Rate Limiting**
```python
# APIs de administração com rate limit especial
admin_modules_endpoints: 10 req/min  # Operações administrativas são lentas
```

---

## 📊 **Monitoramento e Observabilidade**

### **Health Checks Automáticos**
```python
# Cada service pode expor health check
class UserService:
    async def health_check(self) -> dict:
        try:
            # Testar conexão com BD
            await self.repo.find_by_id("test")
            return {"ok": True, "database": "connected"}
        except Exception as e:
            return {"ok": False, "database": "error", "error": str(e)}

# Container chama automaticamente
health = await container.health_check()
# → {"user_service": {"status": "healthy", "response_time_ms": 45}}
```

### **Metrics por Módulo**
```python
# Automático via logging estruturado
module_load_count{module="auth"}                    # carregamentos
module_status{module="users", status="active"}     # status atual  
service_resolution_time{service="user_service"}    # tempo DI
service_request_count{service="auth_service"}      # uso do service
```

---

## 🔧 **Tools e Scripts**

### **Ferramentas Disponíveis**
```bash
# Gestão de módulos
python scripts/create_module.py {name} "{display}" "{desc}"
python scripts/validate_module.py {name} --detailed
python scripts/populate_module_registry.py --analyze

# BD e schema  
python app/db_schema/create_module_schema.py --drop-existing

# Debug e análise
python -c "
import asyncio
from app.core.service_container import container
print(container.get_stats())
"
```

### **Comandos Úteis**
```sql
-- Ver módulos registrados
SELECT id, name, status, kind, load_count FROM modules ORDER BY display_order;

-- Ver dependências
SELECT m.name, dep.depends_on, dep.required 
FROM modules m 
JOIN module_dependencies dep ON m.id = dep.module_id;

-- Health checks recentes
SELECT module_id, status, message, checked_at
FROM module_health_checks 
WHERE checked_at > NOW() - INTERVAL '1 hour'
ORDER BY checked_at DESC;
```

---

## 🎯 **Migration Plan**

### **Implementação Gradual**
```python
# 1. Criar infrastructure (não quebra nada)
✅ Schema BD
✅ ServiceContainer  
✅ ModuleRegistry
✅ Admin APIs

# 2. Migrar um módulo por vez
- Manter sistema atual funcionando
- auth → container DI
- users → container DI  
- agents → container DI

# 3. Deprecar sistema antigo
- Remover api_loader.py
- Remover controller_loader.py
- Limpeza final
```

### **Zero Downtime**
- ✅ **Backward compatibility** - sistema atual continua funcionando
- ✅ **Gradual migration** - um módulo por vez
- ✅ **Rollback plan** - pode voltar ao sistema antigo
- ✅ **Testing** - validar cada migração

**🎉 Com este sistema, vocês terão administração completa de módulos via API, configuração dinâmica e dependency injection profissional!**

**Quer que eu implemente alguma das fases como demonstração prática?** 🚀