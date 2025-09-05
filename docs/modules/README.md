# 📚 Documentação Completa de Módulos

Esta é a **documentação principal** sobre como criar, estruturar e manter módulos na Plataforma de Agentes de Desenvolvimento.

## 🎯 **Visão Geral**

Nossa plataforma usa uma **arquitetura modular** onde cada funcionalidade é implementada como um módulo independente que segue **contratos bem definidos**.

**Benefícios:**
- ✅ **Desenvolvimento paralelo** - teams podem trabalhar em módulos separadamente
- ✅ **Reutilização** - módulos podem ser usados em diferentes contextos  
- ✅ **Manutenibilidade** - falhas são isoladas, atualizações são seguras
- ✅ **Escalabilidade** - adicionar funcionalidades sem impactar sistema existente

---

## 📋 **Documentação de Contratos**

### **📂 [Contratos de Módulos](../contracts/modules/)**
Documentação **obrigatória** que define como todos os módulos devem ser implementados:

| Documento | Foco | Quando Usar |
|-----------|------|-------------|
| **[📋 README](../contracts/modules/README.md)** | Visão geral completa | Começando com módulos |
| **[🎯 Contratos de Interface](../contracts/modules/interface-contracts.md)** | Princípios, responsabilidades | Planejando novos módulos |
| **[🌐 Contratos de API](../contracts/modules/api-contracts.md)** | REST, rotas, schemas | Implementando endpoints |
| **[⚙️ Contratos de Implementação](../contracts/modules/implementation-contracts.md)** | Services, repositories | Estrutura interna |
| **[🛠️ Guia de Scaffolding](../contracts/modules/scaffolding-guide.md)** | Templates, automação | Criação rápida |

---

## 🚀 **Como Criar um Novo Módulo**

### **Método Rápido (Recomendado)**
```bash
# 1. Gerar estrutura automática
python scripts/create_module.py products "Gestão de Produtos" "CRUD produtos e-commerce"

# 2. Validar conformidade  
python scripts/validate_module.py products

# 3. Implementar lógica específica
# - Editar schemas.py com campos do módulo
# - Implementar validações de negócio no service
# - Criar repository SQL se necessário

# 4. Testar
pytest tests/products/ -v
uvicorn app.main:app --reload
```

### **Método Manual (Para Casos Complexos)**
1. **📖 Ler** [Contratos de Interface](../contracts/modules/interface-contracts.md)
2. **🎯 Definir** responsabilidade única do módulo  
3. **📝 Planejar** APIs seguindo [Contratos de API](../contracts/modules/api-contracts.md)
4. **⚙️ Implementar** seguindo [Contratos de Implementação](../contracts/modules/implementation-contracts.md)
5. **✅ Validar** com checklist de conformidade

---

## 📊 **Módulos Existentes**

### **Módulos do Sistema**
| Módulo | Status | Descrição | Endpoint Base |
|--------|:------:|-----------|---------------|
| **auth** | ✅ | Autenticação JWT, sessões | `/v1/auth/` |
| **users** | ⚠️ | CRUD usuários, perfis | `/v1/users/` |
| **agents** | 🔄 | Agentes IA especializados | `/v1/agents/` |
| **workspace** | 🔄 | Gestão de projetos | `/v1/workspace/` |
| **code** | 🔄 | Operações de código | `/v1/code/` |
| **execution** | 🔄 | Execução segura | `/v1/execution/` |

**Legenda:**
- ✅ **Conforme** - segue todos os contratos
- ⚠️ **Necessita ajustes** - pequenas correções  
- 🔄 **Em desenvolvimento** - ainda sendo implementado

### **Casos de Uso para Novos Módulos**
- **`products`** - E-commerce, catálogo
- **`notifications`** - Alertas, mensagens
- **`reports`** - Relatórios, analytics  
- **`integrations`** - APIs externas
- **`files`** - Upload, storage, CDN
- **`billing`** - Pagamentos, assinaturas

---

## 🏗️ **Arquitetura de Módulos**

### **Estrutura Física**
```
app/app/
├── api/{module}/              # 🌐 HTTP endpoints
│   ├── routes.py              # FastAPI router
│   ├── schemas.py             # Pydantic models
│   ├── dependencies.py        # Auth, validações
│   └── __init__.py            # Exports
├── services/                  # ⚙️ Business logic
│   ├── {module}_service.py    # Service principal
│   └── {module}_wiring.py     # DI factory
└── repositories/              # 💾 Data access
    └── sql_repos.py           # Implementações SQL
```

### **Fluxo de Dados**
```
HTTP Request
    ↓
routes.py (validação HTTP)
    ↓  
schemas.py (validação dados)
    ↓
service.py (lógica negócio)  
    ↓
repository.py (persistência)
    ↓
Database
```

### **Carregamento Automático**
```python
# app/main.py carrega todos os módulos automaticamente
from app.core.api_loader import include_api_modules
include_api_modules(app)  # Descobre e inclui todos os app/api/*/routes.py
```

---

## 🛡️ **Segurança por Módulo**

### **Níveis de Proteção**
```python
# Público (sem auth)
@router.post("/login")

# Autenticado (require_user)  
@router.get("/me", dependencies=[Depends(require_user)])

# Admin (require_admin)
@router.get("/", dependencies=[Depends(require_admin)])

# Sistema (verify_api_key)
@router.get("/internal/health", dependencies=[Depends(verify_api_key)])
```

### **Rate Limiting**
```python
# Por módulo - configurável
auth_endpoints: 5 req/min por IP
users_endpoints: 100 req/min por user
agents_endpoints: 20 req/min por user (AI é caro)
```

---

## 🧪 **Testes e Qualidade**

### **Estrutura de Testes** 
```
tests/{module}/
├── test_api.py           # Testes de endpoints
├── test_service.py       # Testes de lógica de negócio  
├── test_repository.py    # Testes de persistência
└── conftest.py          # Fixtures compartilhadas
```

### **Coverage Mínima**
```python
# Por módulo
API Layer: 90%+ (crítico para contratos)
Service Layer: 85%+ (lógica de negócio)  
Repository Layer: 80%+ (queries SQL)
```

### **Comandos de Teste**
```bash
# Teste específico do módulo
pytest tests/{module}/ -v --cov=app.api.{module} --cov=app.services.{module}

# Todos os módulos
pytest tests/ --cov=app --cov-report=html

# Linting  
black app/api/{module}/ app/services/{module}_*
flake8 app/api/{module}/ app/services/{module}_*  
mypy app/api/{module}/ app/services/{module}_*
```

---

## 📈 **Monitoramento e Observabilidade**

### **Metrics por Módulo**
```python
# Automático via logging estruturado
requests_total{module="users", endpoint="/me", status="200"}
request_duration_seconds{module="users", endpoint="/me"} 
error_total{module="users", error_code="ERR_USER_NOT_FOUND"}
```

### **Health Checks**
```python
# Cada módulo pode expor (opcional):
@router.get("/health")
async def module_health():
    return {
        "status": "healthy",
        "module": "{module_name}",
        "version": "1.0.0",
        "dependencies": {
            "database": "healthy",
            "external_api": "degraded",  # se aplicável
        }
    }
```

---

## 🔄 **Evolução e Versionamento**

### **Versionamento de APIs** 
```python
# Manter compatibilidade
/v1/{module}/  # versão atual, estável
/v2/{module}/  # nova versão, breaking changes

# Deprecação gradual
@router.get("/legacy-endpoint")
@deprecated("Use /v2/new-endpoint instead")
async def old_endpoint(): ...
```

### **Migration Path**
1. **Preparação** - implementar nova versão em paralelo
2. **Comunicação** - notificar clientes sobre mudanças
3. **Rollout** - migração gradual de clientes
4. **Cleanup** - remoção da versão antiga

---

## 🎯 **Caso de Estudo Real: Auth vs Users**

### **Situação Atual (problemática)**
```python
# auth/schemas.py define User completo
class User(BaseModel):
    id: str
    login: str  
    nome: str          # ← deveria estar em users
    email: str         # ← deveria estar em users
    isAdmin: bool      # ← ok para auth
    # ...

# users/routes.py importa de auth  
from app.api.auth.schemas import User  # ← dependência incorreta
```

### **Situação Ideal (após refactor)**
```python
# auth/schemas.py - dados mínimos
class AuthUser(BaseModel):
    id: str
    login: str
    isAdmin: bool
    status: str
    # SEM: nome, email, whatsapp, ui, modules

# users/schemas.py - dados completos  
class User(BaseModel):
    id: str
    login: str
    nome: Optional[str]
    email: Optional[str]
    # ... todos os campos de perfil
```

**Benefício:** Módulos **independentes** com responsabilidades **claras**.

---

## 🛠️ **Ferramentas de Desenvolvimento**

### **Scripts Disponíveis**
```bash
# Geração
scripts/create_module.py          # Criar novo módulo
scripts/create_module_test.py     # Gerar só testes  

# Validação
scripts/validate_module.py        # Verificar conformidade
scripts/check_contracts.py        # Audit completo
scripts/analyze_dependencies.py   # Detectar dependências circulares

# Manutenção
scripts/update_module_templates.py  # Atualizar templates
scripts/migrate_module.py          # Migrar para nova versão de contratos
```

### **IDE Extensions (futuro)**
- **Snippets** para VS Code com templates de módulo
- **Linting rules** para verificar conformidade  
- **IntelliSense** para APIs dos módulos

---

## 📖 **Documentação Complementar**

### **Conceitos Avançados**
- [🔄 Comunicação Entre Módulos](../development/inter-module-communication.md)
- [🎛️ Configuração e Environment](../ops/module-configuration.md)  
- [📊 Monitoramento e Alertas](../ops/module-monitoring.md)

### **Guias Específicos**
- [🤖 Módulos com IA](../guidelines/ai-modules.md)
- [⬆️ Módulos com Upload](../guidelines/upload-modules.md)
- [📡 Módulos de Integração](../guidelines/integration-modules.md)

### **Troubleshooting**
- [🐛 Problemas Comuns](../development/troubleshooting.md)
- [🔍 Debug de Módulos](../development/debugging.md)

---

## ✨ **Próximos Passos**

### **Para Desenvolvedores**
1. **📖 Ler** a documentação de contratos completa
2. **🧪 Testar** criando um módulo simples com o script
3. **🔄 Refatorar** módulos existentes para conformidade
4. **📝 Dar feedback** sobre dificuldades encontradas

### **Para o Sistema**
1. **🔄 Migrar** módulos existentes para nova estrutura
2. **🛠️ Implementar** ferramentas de validação automática
3. **📊 Configurar** monitoramento por módulo
4. **📚 Expandir** documentação com casos reais

---

**🎉 Agora você tem TUDO que precisa para criar módulos profissionais, seguros e escaláveis!**

**👥 Questions? Issues? Feedback?** Use os canais da documentação ou abra um issue no repositório.