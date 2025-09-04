# 🔄 Demonstração: Migração Auth + Users para Novo Sistema

Esta demonstração mostra **como migrar** os módulos auth e users existentes para o **novo sistema de registry e service container**.

## 🎯 **Objetivo da Migração**

Transformar:
- ❌ **Services inconsistentes** → ✅ **DI centralizado**
- ❌ **Configuração hardcoded** → ✅ **Configuração dinâmica**  
- ❌ **Sem administração** → ✅ **Admin APIs completas**
- ❌ **Estado em memória** → ✅ **Registry persistido**

---

## 📊 **ANTES: Situação Atual (Problemática)**

### **Service Instantiation - Inconsistente**
```python
# app/api/auth/routes.py
auth_service = build_auth_service_from_settings()  # ← Global, singleton

# app/api/users/routes.py  
service = UserService()  # ← Local, nova instância toda request

# app/controllers/user_controller.py (legado)
service = UserService()  # ← Outra instância, duplicação
```

### **Configuração - Hardcoded**
```python
# app/config/settings.py
JWT_SECRET_KEY = "hardcoded-secret"
ACCESS_TTL_SEC = 900
REFRESH_TTL_SEC = 86400

# Para mudar: restart obrigatório
```

### **Sem Administração Central**
```python
# Não existe:
# - API para listar módulos
# - Ativar/desativar módulos  
# - Alterar configuração sem restart
# - Health monitoring
```

---

## ✅ **DEPOIS: Novo Sistema (Estruturado)**

### **1. Module Registry (BD)**
```sql
-- Módulos persistidos no BD
INSERT INTO modules (id, name, kind, version, status, config) VALUES 
('auth', 'Sistema de Autenticação', 'system', '1.0.0', 'active', 
 '{"access_ttl_sec": 900, "refresh_ttl_sec": 86400, "rate_limit_per_ip": 5}'),
('users', 'Gestão de Usuários', 'system', '1.0.0', 'active',
 '{"password_min_length": 8, "max_users": 1000, "enable_whatsapp": true}');

-- Dependências explícitas
INSERT INTO module_dependencies (module_id, depends_on, required) VALUES
('users', 'auth', true);
```

### **2. Service Container (DI)**
```python
# Container centralizado
container = ServiceContainer()

# Registro dos services
container.register(
    "auth_service", 
    AuthService,
    build_auth_service_from_settings,
    module_id="auth",
    singleton=True
)

container.register(
    "user_service",
    UserService, 
    build_user_service_with_config,
    module_id="users",
    singleton=True,
    dependencies=["user_repo", "audit_repo"]
)

# Resolução automática
auth_service = await container.get("auth_service")  # ← Singleton real
user_service = await container.get("user_service")  # ← Com DI automático
```

### **3. Routes Migrados (DI)**
```python
# app/api/users/routes.py (MIGRADO)

# ANTES:
service = UserService()  # ← Instância local

@router.get("/{user_id}")
async def get_user(user_id: str):
    user = await service.get_user_by_id(user_id)  # ← Service local

# DEPOIS:  
async def get_user_service() -> UserService:
    """Dependency injection do container."""
    return await container.get("user_service")

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service)  # ← DI do container
):
    user = await service.get_user_by_id(user_id)  # ← Service do container
```

### **4. Admin APIs (Gestão)**
```python
# Novos endpoints de administração

GET    /v1/admin/modules/              # Lista módulos do registry
GET    /v1/admin/modules/auth/config   # Config atual do auth
PUT    /v1/admin/modules/auth/config   # Alterar TTL, rate limits
POST   /v1/admin/modules/auth/reload   # Aplicar mudanças sem restart

GET    /v1/admin/modules/stats         # Stats do sistema
GET    /v1/admin/container/stats       # Stats do DI container
```

---

## 🚀 **Demonstração Prática**

### **Passo 1: Registry Setup**
```python
# Módulos registrados automaticamente:

auth_module = {
    "id": "auth",
    "name": "Sistema de Autenticação",
    "kind": "system", 
    "version": "1.0.0",
    "status": "active",
    "config": {
        "access_ttl_sec": 900,      # ← Configurável
        "refresh_ttl_sec": 86400,   # ← Configurável  
        "rate_limit_per_ip": 5,     # ← Configurável
        "enable_password_reset": true
    }
}

users_module = {
    "id": "users", 
    "name": "Gestão de Usuários",
    "status": "active",
    "config": {
        "password_min_length": 8,
        "max_users": 1000,
        "enable_whatsapp": true,
        "default_modules": ["auth", "workspace"]
    },
    "dependencies": [{"module": "auth", "required": true}]
}
```

### **Passo 2: Service Container Registration**
```python
# Startup da aplicação:

# 1. Registrar AuthService
container.register(
    "auth_service",
    AuthService,
    lambda: build_auth_service_with_config(auth_module.config),  # ← Config dinâmica
    module_id="auth",
    singleton=True
)

# 2. Registrar UserService com dependências
container.register(
    "user_service", 
    UserService,
    lambda user_repo, audit_repo: UserService(user_repo, audit_repo, users_module.config),
    module_id="users",
    dependencies=["user_repo", "audit_repo"]  # ← DI automático
)

# 3. Services criados sob demanda
auth_service = await container.get("auth_service")  # ← Cria e cacheia
user_service = await container.get("user_service")  # ← Resolve deps e cria
```

### **Passo 3: Routes Migration**
```python
# app/api/auth/routes.py (MIGRADO)

# ANTES:
auth_service = build_auth_service_from_settings()  # ← Global

@router.post("/login")
async def login(body: LoginRequest):
    bundle = await auth_service.login(...)  # ← Service global

# DEPOIS:
async def get_auth_service() -> AuthService:
    return await container.get("auth_service")

@router.post("/login")
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)  # ← DI
):
    bundle = await auth_service.login(...)  # ← Service do container
    # Bonus: auth_service tem config dinâmica do registry!
```

### **Passo 4: Admin APIs em Ação**
```http
# Alterar TTL do token sem restart:

PUT /v1/admin/modules/auth/config
{
  "access_ttl_sec": 1800,     # ← Era 900, agora 30min
  "refresh_ttl_sec": 172800,  # ← Era 86400, agora 48h
  "rate_limit_per_ip": 10     # ← Era 5, agora 10 req/min
}

POST /v1/admin/modules/auth/reload
→ AuthService recria com nova configuração
→ Próximos logins usam TTL de 30min
→ SEM RESTART da aplicação!
```

---

## 🎯 **Resultados da Migração**

### **✅ Service Management**
```python
# Stats do container após migração:
{
  "registered_services": 4,      # auth_service, user_service, user_repo, audit_repo
  "active_instances": 4,         # Singletons ativos
  "modules_with_services": 3,    # auth, users, core
  "total_resolutions": 12,       # Quantas vezes services foram resolvidos
  "modules": {
    "auth": 1,    # 1 service (auth_service)
    "users": 1,   # 1 service (user_service)  
    "core": 2     # 2 shared repos
  }
}
```

### **✅ Module Registry**
```python
# Módulos no registry:
[
  {
    "id": "auth",
    "name": "Sistema de Autenticação", 
    "status": "active",
    "loadCount": 1,
    "lastLoaded": "2024-01-15T10:30:00Z",
    "config": {"access_ttl_sec": 1800}  # ← Configuração atual
  },
  {
    "id": "users",
    "name": "Gestão de Usuários",
    "status": "active", 
    "dependencies": ["auth"],
    "config": {"max_users": 1000}
  }
]
```

### **✅ Health Monitoring**
```python
# Health check automático:
{
  "auth_service": {
    "status": "healthy",
    "response_time_ms": 45,
    "instance_id": "abc-123",
    "request_count": 156
  },
  "user_service": {
    "status": "healthy", 
    "response_time_ms": 23,
    "dependencies": ["user_repo", "audit_repo"]
  }
}
```

---

## 🔄 **Demonstração dos Cenários**

### **Cenário 1: Alterar TTL de Token**
```bash
# Situação: Queremos mudar TTL de 15min para 30min

# ANTES (sistema atual):
# 1. Editar app/config/settings.py
# 2. Restart da aplicação
# 3. Downtime durante restart

# DEPOIS (novo sistema):
curl -X PUT /v1/admin/modules/auth/config \\
  -H "Authorization: Bearer admin-token" \\
  -d '{"access_ttl_sec": 1800}'
  
curl -X POST /v1/admin/modules/auth/reload \\
  -H "Authorization: Bearer admin-token"

# Resultado: TTL alterado SEM RESTART! 🎉
```

### **Cenário 2: Debugar Problema de Performance**
```bash
# Ver stats dos services:
GET /v1/admin/container/stats
→ {
    "auth_service": {"request_count": 1543, "response_time_ms": 85},
    "user_service": {"request_count": 2341, "response_time_ms": 120}  # ← Lento!
  }

# Ver configuração atual:  
GET /v1/admin/modules/users/config
→ {"max_users": 1000, "enable_search_index": false}  # ← Causa lentidão

# Otimizar:
PUT /v1/admin/modules/users/config
{"enable_search_index": true, "cache_ttl_sec": 300}

POST /v1/admin/modules/users/reload
→ UserService reconfigura com cache
→ Performance melhora instantaneamente
```

### **Cenário 3: Rollback de Configuração**
```bash
# Configuração nova causou problemas:
PUT /v1/admin/modules/auth/config {"access_ttl_sec": 60}  # TTL muito baixo
POST /v1/admin/modules/auth/reload

# Usuários reclamando de logout frequente...

# Rollback imediato:
PUT /v1/admin/modules/auth/config {"access_ttl_sec": 900}  # Volta ao anterior
POST /v1/admin/modules/auth/reload
→ Problema resolvido em segundos!
```

---

## 📋 **Código da Migração**

### **Service Container Registration**
```python
# app/core/bootstrap.py (novo arquivo)

async def setup_migrated_modules():
    """Setup dos módulos migrados para o container."""
    
    # 1. AuthService com configuração dinâmica
    async def build_auth_service_with_config():
        config = await demo_registry.get_config("auth")
        
        # Build normal + inject config
        service = build_auth_service_from_settings()
        service._dynamic_config = config
        
        # Override methods para usar config dinâmica
        original_get_ttl = service._get_access_ttl
        service._get_access_ttl = lambda: config.get("access_ttl_sec", 900)
        
        return service
    
    container.register(
        "auth_service",
        AuthService, 
        build_auth_service_with_config,
        module_id="auth",
        singleton=True
    )
    
    # 2. UserService com DI e config
    async def build_user_service_with_di(**deps):
        config = await demo_registry.get_config("users")
        
        # UserService atual não usa DI no constructor ainda
        # Mas podemos preparar para futuro:
        service = UserService()
        service._config = config
        service._user_repo = deps.get("user_repo")  # Preparar para DI
        service._audit_repo = deps.get("audit_repo")
        
        return service
    
    # Repositories compartilhados
    container.register("user_repo", PgUserRepo, PgUserRepo, module_id="core", singleton=True)
    container.register("audit_repo", PgAuditLogRepo, PgAuditLogRepo, module_id="core", singleton=True)
    
    # UserService
    container.register(
        "user_service",
        UserService,
        build_user_service_with_di, 
        module_id="users",
        dependencies=["user_repo", "audit_repo"]
    )
```

### **Routes Migration**
```python
# app/api/auth/routes.py (MIGRADO)

# ANTES:
auth_service = build_auth_service_from_settings()

@router.post("/login")
async def login(req: Request, body: LoginRequest):
    bundle = await auth_service.login(...)

# DEPOIS:
async def get_auth_service() -> AuthService:
    """Dependency injection do container."""
    return await container.get("auth_service")

@router.post("/login") 
async def login(
    req: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)  # ← DI!
):
    # Service vem do container, com config dinâmica
    bundle = await auth_service.login(...)
    
    # Bonus: pode acessar config atual
    config = getattr(auth_service, '_dynamic_config', {})
    logger.info("login.config", extra={"ttl": config.get("access_ttl_sec")})
```

### **Admin APIs**
```python
# app/api/admin/modules_routes.py (NOVO)

@router.get("/modules")
async def list_modules(admin: CurrentUser = Depends(require_admin)):
    """Lista módulos do registry."""
    modules = await registry.list_modules()
    return [{"id": m.id, "status": m.status, "config": m.config} for m in modules]

@router.put("/modules/{id}/config")
async def update_config(module_id: str, config: dict, admin: CurrentUser = Depends(require_admin)):
    """Atualiza configuração dinâmica."""
    await registry.update_config(module_id, config)
    return {"message": "Config atualizada, use /reload para aplicar"}

@router.post("/modules/{id}/reload") 
async def reload_module(module_id: str, admin: CurrentUser = Depends(require_admin)):
    """Hot-reload do módulo."""
    # 1. Unload service atual
    await container.unload_module(module_id)
    
    # 2. Re-register com nova config
    await setup_module(module_id)  # Re-registra no container
    
    return {"message": f"Módulo {module_id} recarregado com sucesso"}
```

---

## 🧪 **Teste da Migração**

### **Test 1: DI Container**
```python
async def test_di_container():
    """Testa se DI está funcionando."""
    
    # 1. Resolver AuthService
    auth1 = await container.get("auth_service")
    auth2 = await container.get("auth_service") 
    assert auth1 is auth2  # ← Singleton real
    
    # 2. Resolver UserService com dependencies
    user_service = await container.get("user_service")
    assert hasattr(user_service, '_user_repo')  # ← Dependency foi injetada
    
    # 3. Stats do container
    stats = container.get_stats()
    assert stats["registered_services"] >= 2
    assert stats["active_instances"] >= 2
    
    print("✅ Container DI funcionando!")
```

### **Test 2: Registry Dinâmico**
```python
async def test_dynamic_config():
    """Testa configuração dinâmica."""
    
    # 1. Config atual
    old_config = await registry.get_config("auth")
    old_ttl = old_config.get("access_ttl_sec", 900)
    
    # 2. Alterar config
    new_config = {**old_config, "access_ttl_sec": 1800}
    await registry.update_config("auth", new_config)
    
    # 3. Verificar mudança
    updated_config = await registry.get_config("auth")
    new_ttl = updated_config.get("access_ttl_sec")
    assert new_ttl == 1800
    
    # 4. Recarregar service (simulado)
    # Em implementação real: container unload + reload
    
    print("✅ Configuração dinâmica funcionando!")
```

### **Test 3: Health Monitoring** 
```python
async def test_health_monitoring():
    """Testa monitoring de módulos."""
    
    # 1. Health check do container
    health = await container.health_check()
    assert "auth_service" in health
    assert "user_service" in health
    
    # 2. Stats dos módulos
    modules = await registry.list_modules()
    auth_module = next(m for m in modules if m.id == "auth")
    assert auth_module.load_count >= 1
    
    # 3. Service performance
    auth_health = health["auth_service"]
    assert auth_health["status"] == "healthy"
    
    print("✅ Health monitoring funcionando!")
```

---

## 📈 **Benefícios Demonstrados**

### **Performance**
```python
# ANTES: Nova instância a cada request
# UserService() ← instanciação custosa

# DEPOIS: Singleton real  
# await container.get("user_service") ← cached, sem overhead
```

### **Configuration**
```python
# ANTES: Restart obrigatório
# settings.ACCESS_TTL_SEC = 1800  # requer restart

# DEPOIS: Hot-reload
# PUT /admin/modules/auth/config + reload ← sem downtime
```

### **Observability**
```python
# ANTES: Sem visibilidade
# Não sabemos quantas instâncias existem

# DEPOIS: Monitoring completo
# container.get_stats() → instâncias, resolutions, performance
```

### **Administration**
```python
# ANTES: Gestão manual
# Editar código → commit → deploy → restart

# DEPOIS: Admin APIs
# UI de admin → API calls → mudanças instantâneas
```

---

## 🎯 **Roteiro de Implementação**

### **Fase 1: Infrastructure (✅ Pronto)**
- [x] Schema BD para registry
- [x] ServiceContainer implementation  
- [x] ModuleRegistryService
- [x] Admin APIs structure
- [x] Mock implementation para demo

### **Fase 2: Migration Auth (Next)**
```python
# 1. Migrar AuthService para container
# 2. Atualizar app/api/auth/routes.py para usar DI
# 3. Testar login/refresh com novo padrão
# 4. Configuração dinâmica funcionando
```

### **Fase 3: Migration Users (Next)**
```python  
# 1. Migrar UserService para container
# 2. Atualizar app/api/users/routes.py para usar DI
# 3. Testar CRUD com novo padrão
# 4. Dependency injection user_repo, audit_repo
```

### **Fase 4: Admin Integration (Next)**
```python
# 1. Ativar admin APIs 
# 2. UI para administração
# 3. Hot-reload funcionando
# 4. Monitoring dashboard
```

---

## 🎉 **Demo Endpoints**

Após migração, estes endpoints estarão disponíveis:

### **Module Management**
```
GET  /v1/admin/modules/           # Lista auth + users no registry
GET  /v1/admin/modules/auth       # Detalhes do módulo auth
PUT  /v1/admin/modules/auth/config # Alterar TTL, rate limits  
POST /v1/admin/modules/auth/reload # Hot-reload do AuthService
```

### **Container Inspection**
```
GET  /v1/admin/container/stats    # Stats do DI container
GET  /v1/admin/modules/auth/services # Services do módulo auth
```

### **Migrated Endpoints (with DI)**
```
POST /v1/auth/login               # AuthService do container  
GET  /v1/users/me                 # UserService do container
GET  /v1/users/{id}               # UserService do container
```

---

**🎊 Esta migração demonstra como transformar o sistema atual em uma arquitetura profissional com:**

✅ **Registry persistente** - módulos salvos no BD  
✅ **DI centralizado** - services gerenciados adequadamente  
✅ **Configuração dinâmica** - mudanças sem restart  
✅ **Admin APIs** - controle total via REST  
✅ **Monitoring** - health checks e performance  
✅ **Hot-reload** - aplicar mudanças instantaneamente  

**Próximo passo:** Implementar esta migração no código real! 🚀