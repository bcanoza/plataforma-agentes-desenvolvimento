# 📋 Contratos de Interface para Módulos

Este documento define os **contratos obrigatórios** que todos os módulos devem seguir na Plataforma de Agentes de Desenvolvimento.

## 🎯 **Princípios Fundamentais**

### **1. Single Responsibility Principle**
Cada módulo deve ter **uma responsabilidade bem definida**:

- ✅ **Bom:** `auth` gerencia tokens, `users` gerencia dados de usuário
- ❌ **Ruim:** `auth` mistura tokens + CRUD de usuários + preferências

### **2. Comunicação Clara Entre Módulos**
Módulos se comunicam através de **contratos bem definidos**:

- ✅ `auth` expõe dados mínimos (`AuthUser`)
- ✅ `users` expõe dados completos (`User`) 
- ✅ Frontend chama ambos conforme necessidade

### **3. Isolamento e Autonomia**
Cada módulo deve ser **independente e testável**:

- ✅ Pode ser desenvolvido/testado isoladamente
- ✅ Tem suas próprias dependências
- ✅ Falha de forma isolada

---

## 📁 **Contrato: Estrutura de Arquivos**

### **Estrutura Obrigatória**
```
app/api/{module_name}/
├── routes.py          # FastAPI router [OBRIGATÓRIO]
├── schemas.py         # Pydantic models [OBRIGATÓRIO]  
├── dependencies.py    # Auth, validações [OPCIONAL]
└── __init__.py        # Exports [OBRIGATÓRIO]
```

### **Exemplo: Módulo Auth**
```python
# app/api/auth/routes.py
router = APIRouter(prefix="/v1/auth", tags=["Authentication"])

# app/api/auth/schemas.py  
class LoginRequest(BaseModel): ...
class LoginResponse(BaseModel): ...
class ErrorResponse(BaseModel): ...

# app/api/auth/dependencies.py
async def require_user() -> CurrentUser: ...
async def verify_api_key() -> bool: ...
```

### **Exemplo: Módulo Users**
```python
# app/api/users/routes.py
router = APIRouter(prefix="/v1/users", tags=["Users"])

# app/api/users/schemas.py
class User(BaseModel): ...
class CreateUserRequest(BaseModel): ...
class UpdateUserRequest(BaseModel): ...
```

---

## 🌐 **Contrato: API REST**

### **Padrão de Rotas** 
Todos os módulos **DEVEM** seguir este padrão:

```python
# Versionado com /v1/
router = APIRouter(prefix="/v1/{module_name}", tags=["{ModuleName}"])
```

### **Operações CRUD Padrão**
```python
# Listagem (se aplicável)
@router.get("/", response_model=List[EntityResponse])

# Busca por ID
@router.get("/{id}", response_model=EntityResponse) 

# Criação
@router.post("/", response_model=EntityResponse, status_code=201)

# Atualização
@router.put("/{id}", response_model=EntityResponse)

# Remoção  
@router.delete("/{id}", status_code=204)
```

### **Rotas Especiais (se necessário)**
```python
# Ação do próprio usuário
@router.get("/me", response_model=EntityResponse)
@router.put("/me/{action}", ...)

# Operações específicas
@router.post("/{id}/{action}", ...)
```

---

## 📝 **Contrato: Schemas Pydantic**

### **Padrões Obrigatórios**

**1. Request Models**
```python
class CreateEntityRequest(BaseModel):
    # Campos obrigatórios primeiro
    name: str
    
    # Campos opcionais depois
    description: Optional[str] = None
    status: str = "active"
    
    # Validações explícitas
    email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

class UpdateEntityRequest(BaseModel):
    # TODOS os campos Optional em updates
    name: Optional[str] = None
    description: Optional[str] = None
```

**2. Response Models**
```python
class Entity(BaseModel):
    # ID sempre presente
    id: str
    
    # Dados do negócio
    name: str
    status: Literal["active", "disabled"]
    
    # Metadados padrão
    createdAt: str
    updatedAt: str
    
    # Dados sensíveis SEMPRE excluídos
    password: Optional[str] = Field(default=None, exclude=True)
```

**3. Error Response (padrão universal)**
```python
class ErrorResponse(BaseModel):
    error: str          # Código erro (ERR_USER_NOT_FOUND) 
    message: str        # Mensagem humana
    details: Optional[Dict[str, Any]] = None
    traceId: Optional[str] = None
```

### **Exemplo Real: Auth vs Users**

**Auth (dados mínimos para tokens):**
```python
class AuthUser(BaseModel):
    """Dados mínimos necessários para JWT"""
    id: str
    login: str
    isAdmin: bool
    status: Literal["active", "disabled"]
    # SEM: email, nome, whatsapp, ui, modules
```

**Users (dados completos):**
```python  
class User(BaseModel):
    """Dados completos de usuário"""
    id: str
    login: str
    nome: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: bool
    status: Literal["active", "disabled"]
    lastLoginAt: Optional[str] = None
    lastLoginIp: Optional[str] = None
    createdAt: str
    updatedAt: str
    ui: Optional[dict] = None
    modules: Optional[List[str]] = None
```

---

## 🔒 **Contrato: Segurança e Autenticação**

### **Níveis de Proteção**

**1. Endpoints Públicos**
```python
@router.post("/login")      # Sem auth
@router.post("/register")   # Sem auth  
```

**2. Endpoints Autenticados**
```python
@router.get("/me", dependencies=[Depends(require_user)])
@router.put("/me/profile", dependencies=[Depends(require_user)])
```

**3. Endpoints Admin**  
```python
@router.get("/", dependencies=[Depends(require_admin)])
@router.delete("/{id}", dependencies=[Depends(require_admin)])
```

**4. Endpoints de Sistema (microserviços)**
```python
@router.get("/internal/health", dependencies=[Depends(verify_api_key)])
```

### **Import de Dependências**
```python
# SEMPRE importar do módulo auth
from app.api.auth.dependencies import require_user, require_admin, verify_api_key
```

---

## 🛡️ **Contrato: Error Handling**

### **Códigos de Erro Padronizados**
```python
# Por módulo - prefixo consistente
auth: ERR_INVALID_CREDENTIALS, ERR_TOKEN_EXPIRED, ERR_USER_DISABLED
users: ERR_USER_NOT_FOUND, ERR_LOGIN_EXISTS, ERR_INVALID_EMAIL  
agents: ERR_AGENT_NOT_FOUND, ERR_CONTEXT_TOO_LARGE
```

### **Status HTTP Mapping**
```python
def _error_response(status_code: int, *, error: str, message: str) -> JSONResponse:
    # Padrão obrigatório para todos os módulos
    payload = ErrorResponse(error=error, message=message).model_dump()
    return JSONResponse(status_code=status_code, content=payload)

# Mapping padrão
status_map = {
    "ERR_NOT_FOUND": 404,
    "ERR_ALREADY_EXISTS": 400, 
    "ERR_FORBIDDEN": 403,
    "ERR_INVALID_*": 400,
    "ERR_EXPIRED_*": 401,
}
```

---

## 📊 **Contrato: Logging e Observabilidade**

### **Padrão de Logging**
```python
logger = get_logger("module_name")

# Estruturado com contexto
logger.info("operation.start", extra={"entity_id": id})
logger.info("operation.ok", extra={"entity_id": id})  
logger.error("operation.fail", extra={"entity_id": id, "error": e.code})
```

### **Eventos de Auditoria**
```python
# Para operações críticas
await audit_log.write(user_id, "user_created", {"target_user": new_user.id})
await audit_log.write(user_id, "password_changed", {"method": "self_service"})
```

---

## 🔄 **Contrato: Comunicação Entre Módulos**

### **Dependências Permitidas**
```python
# ✅ Módulos podem importar de auth (common)
from app.api.auth.dependencies import require_user

# ✅ Módulos podem chamar services compartilhados  
from app.services.user_service import UserService

# ❌ Módulos NÃO devem importar entre si
# from app.api.users.schemas import User  # PROIBIDO
```

### **Dados Compartilhados via API**
```python
# Se users precisa de dados de auth:
# users/routes.py
@router.get("/me/with-session")
async def get_user_with_session(current: CurrentUser = Depends(require_user)):
    # Obtém dados via service compartilhado
    user = await user_service.get_user_by_id(current["sub"])
    session_info = current  # dados do JWT
    return {"user": user, "session": session_info}
```

---

## ✅ **Checklist de Validação**

Para **cada novo módulo**, verifique:

- [ ] **Responsabilidade única** - pode explicar em 1 frase?
- [ ] **Estrutura de arquivos** - routes.py, schemas.py, __init__.py?
- [ ] **Prefix correto** - `/v1/{module_name}`?
- [ ] **Schemas consistentes** - Request/Response/Error?
- [ ] **Error handling** - códigos padronizados + mapping?
- [ ] **Auth apropriada** - public/user/admin/system?
- [ ] **Logging estruturado** - operation.start/ok/fail?
- [ ] **Não importa outros módulos** - só auth.dependencies?
- [ ] **Testes unitários** - cobertura mínima 80%?

---

## 📈 **Próximos Passos**

Esta documentação estabelece os **contratos de interface**. 

Os próximos documentos a criar:
1. **Contratos de API** - detalhes de rotas, parâmetros, paginação
2. **Contratos de Implementação** - services, repositories, wiring
3. **Templates e Scaffolding** - ferramentas para acelerar desenvolvimento

**Case Study Usado:** Separação conceitual auth/users demonstra como aplicar Single Responsibility e comunicação entre módulos.