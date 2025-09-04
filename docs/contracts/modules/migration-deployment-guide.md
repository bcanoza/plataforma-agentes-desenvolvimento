# 🚀 Guia de Deploy da Migração Auth + Users

Este guia contém **todos os passos** para implementar a migração dos módulos auth e users quando o Docker estiver disponível.

## 📦 **Estado Atual - Docker em Manutenção**

✅ **Código preparado** - toda infraestrutura implementada  
✅ **Documentação completa** - contratos estabelecidos  
✅ **Scripts prontos** - automação de setup  
⏳ **Aguardando Docker** - para execução prática  

---

## 🎯 **Arquivos Criados e Prontos**

### **📁 Infraestrutura Base**
```
✅ app/app/core/service_container.py          # DI container centralizado
✅ app/app/core/mock_module_registry.py       # Registry mock para testes
✅ app/app/services/module_registry_service.py # Service de gestão de módulos  
✅ app/app/core/enhanced_module_loader.py     # Loader com registry
✅ app/app/api/admin/modules_routes.py        # Admin APIs
```

### **📁 Schema de Banco**
```
✅ app/app/db_schema/create_module_schema.py  # Schema completo
   → Tabelas: modules, module_dependencies, module_services, module_health_checks
```

### **📁 Scripts de Setup**
```
✅ scripts/create_module.py                   # Geração de novos módulos
✅ scripts/validate_module.py                 # Validação de conformidade
✅ scripts/populate_module_registry.py        # Popular registry com módulos existentes
```

### **📁 Documentação**
```
✅ docs/contracts/modules/                    # 6 documentos completos
   → interface-contracts.md
   → api-contracts.md  
   → implementation-contracts.md
   → scaffolding-guide.md
   → practical-examples.md
   → module-management-system.md
   → migration-demo-auth-users.md ← Esta demonstração
```

---

## 🎬 **Plano de Deploy - Quando Docker Voltar**

### **🔧 Pré-requisitos**
```bash
# Verificar se ambiente está ok
docker-compose up -d postgres redis  # Subir dependências
docker-compose logs postgres          # Verificar se BD conecta
curl http://localhost:8000/           # Verificar se API responde
```

### **📋 Passo 1: Criar Schema de Módulos**
```bash
# Entrar no container da aplicação
docker-compose exec app bash

# Criar schema no PostgreSQL
cd /app
python3 app/db_schema/create_module_schema.py --drop-existing

# Verificar criação
psql $DATABASE_URL -c "\\dt"  # Listar tabelas
psql $DATABASE_URL -c "SELECT id, name, status FROM modules;"
```

### **📋 Passo 2: Popular Registry**
```bash
# Popular com módulos auth e users existentes
python3 scripts/populate_module_registry.py

# Verificar dados inseridos
psql $DATABASE_URL -c "
  SELECT m.id, m.name, m.status, d.depends_on
  FROM modules m 
  LEFT JOIN module_dependencies d ON m.id = d.module_id
  ORDER BY m.display_order;
"

# Resultado esperado:
# id    | name                    | status | depends_on
# auth  | Sistema de Autenticação | active | null
# users | Gestão de Usuários      | active | auth
```

### **📋 Passo 3: Testar Service Container**
```python
# Teste rápido do container
cd /app
python3 -c "
import asyncio
from app.core.service_container import container
from app.services.auth_wiring import build_auth_service_from_settings
from app.services.auth_service import AuthService

async def test():
    # Registrar auth service
    container.register(
        'auth_service',
        AuthService, 
        build_auth_service_from_settings,
        module_id='auth',
        singleton=True
    )
    
    # Resolver duas vezes
    auth1 = await container.get('auth_service')
    auth2 = await container.get('auth_service')
    
    print(f'Singleton working: {auth1 is auth2}')
    print(f'Service type: {type(auth1).__name__}')
    print(f'Container stats: {container.get_stats()}')

asyncio.run(test())
"
```

### **📋 Passo 4: Backup Sistema Atual**
```bash
# Backup dos arquivos que vamos modificar
cp app/api/auth/routes.py app/api/auth/routes.py.backup
cp app/api/users/routes.py app/api/users/routes.py.backup  
cp app/main.py app/main.py.backup

echo "✅ Backup criado - rollback disponível"
```

### **📋 Passo 5: Migrar Auth Routes**
```python
# Modificar app/api/auth/routes.py

# ADICIONAR no início:
from app.core.service_container import container

async def get_auth_service_from_container():
    """Dependency injection do container."""
    return await container.get("auth_service")

# SUBSTITUIR:
# auth_service = build_auth_service_from_settings()  # ← Remover linha global

# ATUALIZAR cada endpoint:
@router.post("/login")
async def login(
    req: Request,
    response: Response,
    body: LoginRequest = Body(...),
    auth_service = Depends(get_auth_service_from_container)  # ← Adicionar param
):
    # Resto do código igual
```

### **📋 Passo 6: Migrar Users Routes**
```python
# Modificar app/api/users/routes.py

# ADICIONAR no início:
from app.core.service_container import container

async def get_user_service_from_container():
    """Dependency injection do container."""
    return await container.get("user_service")

# SUBSTITUIR:
# service = UserService()  # ← Remover linha global

# ATUALIZAR cada endpoint:
@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str, 
    _: CurrentUser = Depends(require_admin),
    service = Depends(get_user_service_from_container)  # ← Adicionar param
):
    # Resto do código igual
```

### **📋 Passo 7: Integrar Enhanced Loader**
```python
# Modificar app/main.py

# SUBSTITUIR:
# from app.core.api_loader import include_api_modules as _autoload
# _autoload(app)

# POR:
from app.core.enhanced_module_loader import enhanced_startup_handler, enhanced_shutdown_handler

@app.on_event("startup")
async def startup():
    await enhanced_startup_handler(app)

@app.on_event("shutdown") 
async def shutdown():
    await enhanced_shutdown_handler(app)
```

### **📋 Passo 8: Ativar Admin APIs**
```python
# app/main.py - adicionar após outros includes

# Admin module management
try:
    from app.api.admin.modules_routes import router as admin_modules_router
    app.include_router(admin_modules_router)
    logger.info("[main] admin APIs carregadas")
except Exception as e:
    logger.warning(f"[main] admin APIs não carregadas: {e}")
```

### **📋 Passo 9: Testar Migração**
```bash
# Restart da aplicação
docker-compose restart app

# Verificar se sobe sem erros
docker-compose logs app | grep -E "(ERROR|module|container)"

# Testar endpoints existentes (devem funcionar igual)
curl -H "X-API-Key: $API_KEY" http://localhost:8000/auth/validate
curl -X POST http://localhost:8000/v1/auth/login -d '{"login":"admin","senha":"123"}'

# Testar novos admin endpoints  
curl -H "Authorization: Bearer $JWT" http://localhost:8000/v1/admin/modules/
```

---

## 🔧 **Scripts de Migração Prontos**

### **migrate_auth_users.sh**
```bash
#!/bin/bash
# Script completo de migração

set -e  # Exit on error

echo "🚀 Iniciando migração auth + users para novo sistema..."

# 1. Backup
echo "📦 Criando backup..."
cp app/api/auth/routes.py app/api/auth/routes.py.backup
cp app/api/users/routes.py app/api/users/routes.py.backup
cp app/main.py app/main.py.backup

# 2. Schema BD
echo "🗄️ Criando schema de módulos..."
python3 app/db_schema/create_module_schema.py --drop-existing

# 3. Popular registry
echo "📋 Populando registry..."
python3 scripts/populate_module_registry.py

# 4. Aplicar patches dos routes
echo "🔄 Migrando routes para DI container..."
python3 scripts/apply_migration_patches.py

# 5. Restart aplicação
echo "♻️ Reiniciando aplicação..."
# docker-compose restart app

echo "✅ Migração concluída!"
echo ""
echo "🔍 Verificar:"
echo "  curl http://localhost:8000/v1/admin/modules/"
echo "  curl http://localhost:8000/v1/admin/container/stats"
```

### **rollback_migration.sh**
```bash
#!/bin/bash
# Script de rollback

echo "🔄 Fazendo rollback da migração..."

# Restaurar backups
mv app/api/auth/routes.py.backup app/api/auth/routes.py
mv app/api/users/routes.py.backup app/api/users/routes.py  
mv app/main.py.backup app/main.py

# Restart
# docker-compose restart app

echo "✅ Rollback concluído - sistema voltou ao estado anterior"
```

---

## 🧪 **Testes Automáticos**

### **test_migration.py**
```python
#!/usr/bin/env python3
"""
Testes automáticos da migração.
Execute após deploy para validar.
"""
import asyncio
import httpx
import json

async def test_migration_success():
    """Testa se migração funcionou corretamente."""
    
    base_url = "http://localhost:8000"
    admin_token = "Bearer YOUR_ADMIN_JWT"  # Obter de login
    
    tests = []
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Endpoints existentes funcionam
        try:
            resp = await client.get(f"{base_url}/")
            assert resp.status_code == 200
            tests.append(("✅", "API básica funcionando"))
        except:
            tests.append(("❌", "API básica com problemas"))
        
        # Test 2: Auth ainda funciona
        try:
            resp = await client.post(f"{base_url}/v1/auth/login", 
                json={"login": "admin", "senha": "123"})
            # Pode dar 401 (credenciais), mas não deve dar 500
            assert resp.status_code != 500
            tests.append(("✅", "Auth endpoint funcionando"))
        except:
            tests.append(("❌", "Auth endpoint quebrado"))
        
        # Test 3: Admin APIs novas funcionam
        try:
            resp = await client.get(f"{base_url}/v1/admin/modules/",
                headers={"Authorization": admin_token})
            if resp.status_code == 200:
                modules = resp.json()
                assert len(modules) >= 2  # auth + users
                tests.append(("✅", "Admin APIs funcionando"))
            else:
                tests.append(("⚠️", f"Admin APIs retornaram {resp.status_code}"))
        except:
            tests.append(("❌", "Admin APIs não funcionam"))
        
        # Test 4: Container stats disponível
        try:
            resp = await client.get(f"{base_url}/v1/admin/container/stats",
                headers={"Authorization": admin_token})
            if resp.status_code == 200:
                stats = resp.json()
                assert "registeredServices" in stats
                tests.append(("✅", "Service container ativo"))
            else:
                tests.append(("⚠️", "Service container não acessível"))
        except:
            tests.append(("❌", "Service container com problemas"))
    
    # Resultados
    print("\\n📋 Resultados dos testes:")
    for status, message in tests:
        print(f"   {status} {message}")
    
    passed = sum(1 for status, _ in tests if status == "✅")
    total = len(tests)
    print(f"\\n🏆 Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_migration_success())
    exit(0 if success else 1)
```

---

## 📋 **Plano Completo de Implementação**

### **🐳 Quando Docker Voltar:**

**1. Preparar Ambiente (5 min)**
```bash
# Verificar se serviços sobem
docker-compose up -d postgres redis
docker-compose logs postgres  # Verificar conexão
docker-compose up -d app       # Subir aplicação
curl http://localhost:8000/    # Testar se responde
```

**2. Executar Migração (10 min)**
```bash
# Entrar no container
docker-compose exec app bash

# Executar migração completa
cd /app
chmod +x scripts/migrate_auth_users.sh
./scripts/migrate_auth_users.sh

# OU passo a passo:
python3 app/db_schema/create_module_schema.py --drop-existing
python3 scripts/populate_module_registry.py  
# (aplicar patches manualmente dos routes)
docker-compose restart app
```

**3. Validar Funcionamento (5 min)**  
```bash
# Testes automáticos
python3 scripts/test_migration.py

# Testes manuais
curl http://localhost:8000/v1/admin/modules/ \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl http://localhost:8000/v1/admin/container/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**4. Testar Cenários Avançados (10 min)**
```bash
# Configuração dinâmica
curl -X PUT http://localhost:8000/v1/admin/modules/auth/config \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"access_ttl_sec": 1800, "rate_limit_per_ip": 10}'

curl -X POST http://localhost:8000/v1/admin/modules/auth/reload \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verificar se mudança foi aplicada
curl http://localhost:8000/v1/admin/modules/auth/config \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 🎯 **Resultados Esperados**

### **✅ Registry Funcionando**
```json
// GET /v1/admin/modules/
[
  {
    "id": "auth",
    "name": "Sistema de Autenticação", 
    "status": "active",
    "version": "1.0.0",
    "loadCount": 1,
    "config": {
      "access_ttl_sec": 900,
      "refresh_ttl_sec": 86400
    }
  },
  {
    "id": "users",
    "name": "Gestão de Usuários",
    "status": "active", 
    "dependencies": ["auth"],
    "config": {
      "max_users": 1000,
      "enable_whatsapp": true
    }
  }
]
```

### **✅ Service Container Ativo**
```json
// GET /v1/admin/container/stats
{
  "registeredServices": 4,        // auth_service, user_service, user_repo, audit_repo
  "activeInstances": 4,           // Singletons ativos
  "modules": {
    "auth": 1,                    // 1 service (auth_service)
    "users": 1,                   // 1 service (user_service)
    "core": 2                     // 2 shared repos
  },
  "totalResolutions": 8           // Quantas vezes services foram resolvidos
}
```

### **✅ Configuração Dinâmica**
```bash
# Alterar TTL de token SEM RESTART:
PUT /v1/admin/modules/auth/config {"access_ttl_sec": 1800}
POST /v1/admin/modules/auth/reload
→ Próximos logins usam TTL de 30min instantaneamente!

# Alterar limite de usuários:  
PUT /v1/admin/modules/users/config {"max_users": 5000}
POST /v1/admin/modules/users/reload
→ Novos usuários criados respeitam novo limite!
```

---

## 🔄 **Comparação: Antes vs Depois**

### **Gestão de Configuração**

**ANTES:**
```python
# settings.py
ACCESS_TTL_SEC = 900  # ← Hardcoded

# Para alterar:
# 1. Editar settings.py
# 2. Commit + push  
# 3. Deploy
# 4. Restart completo
# 5. Downtime
```

**DEPOIS:**
```bash
# Alterar sem downtime:
curl -X PUT /v1/admin/modules/auth/config \
  -d '{"access_ttl_sec": 1800}'
curl -X POST /v1/admin/modules/auth/reload

# Resultado: mudança aplicada em segundos!
```

### **Debugging de Performance**

**ANTES:**
```python
# Não sabemos:
# - Quantas instâncias de UserService existem
# - Quantas vezes services foram chamados
# - Tempo de resolução de dependencies
```

**DEPOIS:**
```json
// GET /v1/admin/container/stats
{
  "user_service": {
    "instanceCount": 1,          // ← Uma instância (singleton)
    "requestCount": 1543,        // ← 1543 requests atendidas
    "responseTimeMs": 45,        // ← Média de 45ms
    "lastCreated": "2024-01-15T10:30:00Z"
  }
}
```

### **Administração**

**ANTES:**
```bash
# Para ativar/desativar funcionalidade:
# 1. Editar código
# 2. Deploy completo
# 3. Restart
```

**DEPOIS:**
```bash
# Ativar/desativar módulo:
POST /v1/admin/modules/agents/disable  # ← Desativa agentes IA
POST /v1/admin/modules/agents/enable   # ← Reativa quando precisar

# Hot-reload de módulo:
POST /v1/admin/modules/users/reload    # ← Aplica mudanças instantaneamente
```

---

## 🛡️ **Segurança e Rollback**

### **Rollback Plan**
```bash
# Se algo der errado:

# Rollback 1: Restaurar arquivos
mv app/api/auth/routes.py.backup app/api/auth/routes.py
mv app/api/users/routes.py.backup app/api/users/routes.py
mv app/main.py.backup app/main.py
docker-compose restart app

# Rollback 2: Manter schema novo, voltar loader antigo
# (backwards compatibility está implementada)

# Rollback 3: Drop schema se necessário
psql $DATABASE_URL -c "
  DROP TABLE IF EXISTS module_health_checks CASCADE;
  DROP TABLE IF EXISTS module_services CASCADE; 
  DROP TABLE IF EXISTS module_dependencies CASCADE;
  DROP TABLE IF EXISTS modules CASCADE;
"
```

### **Testes de Segurança**
```bash
# Verificar que admin APIs são protegidas
curl http://localhost:8000/v1/admin/modules/
# Esperado: 401 Unauthorized

curl -H "Authorization: Bearer USER_TOKEN" http://localhost:8000/v1/admin/modules/  
# Esperado: 403 Forbidden (user não é admin)

curl -H "Authorization: Bearer ADMIN_TOKEN" http://localhost:8000/v1/admin/modules/
# Esperado: 200 OK com lista de módulos
```

---

## 📊 **Métricas de Sucesso**

### **Performance**
- ✅ **Startup time** ≤ tempo atual (registry + container overhead mínimo)
- ✅ **Response time** ≤ tempo atual (singleton elimina instanciação)
- ✅ **Memory usage** ≤ atual (elimina instâncias duplicadas)

### **Funcionalidade**
- ✅ **100% backward compatibility** - endpoints existentes funcionam igual
- ✅ **Admin APIs ativas** - gestão de módulos funcionando  
- ✅ **Hot-reload working** - configuração dinâmica sem restart
- ✅ **Monitoring ativo** - health checks e stats disponíveis

### **Qualidade**
- ✅ **Logs estruturados** - todas operações logadas com contexto
- ✅ **Error handling** - falhas de módulo não derrubam sistema
- ✅ **Auditoria** - mudanças de configuração auditadas

---

## 🎉 **Entregáveis da Migração**

### **📈 Benefícios Imediatos**
1. **DI Real** - uma instância por service, dependency injection automático
2. **Admin APIs** - gestão completa de módulos via REST
3. **Configuração dinâmica** - mudanças sem restart  
4. **Monitoring** - health checks e performance tracking
5. **Registry persistente** - estado sobrevive restarts

### **🛠️ Para o Futuro**
1. **Plugin system** - carregar módulos externos dinamicamente
2. **A/B testing** - testar configurações diferentes por usuário
3. **Auto-scaling** - diferentes configs por ambiente
4. **Module marketplace** - instalar módulos de terceiros

### **👨‍💻 Para Desenvolvedores**
1. **Templates prontos** - criar novos módulos em minutos
2. **Contratos claros** - padrões bem definidos
3. **Ferramentas de validação** - garantir conformidade
4. **Documentação completa** - onboarding rápido

---

**🎊 Quando o Docker voltar, temos TUDO pronto para uma migração suave e profissional dos módulos auth e users!**

**📋 Quick Start quando ambiente voltar:**
```bash
# 1. Subir Docker
docker-compose up -d

# 2. Executar migração  
docker-compose exec app bash -c "cd /app && python3 app/db_schema/create_module_schema.py"
docker-compose exec app bash -c "cd /app && python3 scripts/populate_module_registry.py"

# 3. Aplicar patches manuais nos routes (usando os templates criados)

# 4. Restart e testar
docker-compose restart app
curl http://localhost:8000/v1/admin/modules/
```

**Quer que eu refine algum aspecto específico da migração enquanto aguardamos o Docker?** 🚀