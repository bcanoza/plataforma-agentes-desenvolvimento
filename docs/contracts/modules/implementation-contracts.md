# ⚙️ Contratos de Implementação para Módulos

Este documento define os **contratos de implementação interna** que todos os módulos devem seguir.

## 🏗️ **Arquitetura em Camadas**

### **Visão Geral das Camadas**
```
┌─────────────────┐
│   Routes.py     │ ← FastAPI endpoints, validação HTTP
├─────────────────┤
│   Schemas.py    │ ← Pydantic models, validação dados  
├─────────────────┤
│   Service.py    │ ← Lógica de negócio, orquestração
├─────────────────┤
│   Repository.py │ ← Persistência, queries SQL
└─────────────────┘
```

### **Exemplo: Módulo Users**
```
app/
├── api/users/
│   ├── routes.py           # HTTP layer
│   ├── schemas.py          # Data validation
│   └── dependencies.py     # Auth layer
├── services/
│   ├── user_service.py     # Business logic
│   └── user_wiring.py      # DI container  
└── repositories/
    └── sql_repos.py        # Data access (PgUserRepo)
```

---

## 📦 **Contrato: Services (Lógica de Negócio)**

### **Estrutura Obrigatória**
```python
# app/services/{module}_service.py

@dataclass
class EntityModel:
    """Model de domínio - representa a entidade"""
    id: str
    name: str
    status: str
    createdAt: str
    updatedAt: str

@dataclass  
class CreateEntityInput:
    """DTO para criação"""
    name: str
    status: str = "active"

@dataclass
class UpdateEntityInput:
    """DTO para atualização"""  
    name: Optional[str] = None
    status: Optional[str] = None

class EntityService:
    """Service principal do módulo"""
    
    def __init__(self, entity_repo: EntityRepo, audit_repo: AuditLogRepo):
        self.repo = entity_repo
        self.audit = audit_repo
    
    async def get_entity_by_id(self, entity_id: str) -> Optional[EntityModel]:
        """Busca por ID - método obrigatório"""
        return await self.repo.find_by_id(entity_id)
    
    async def list_entities(self, *, q: Optional[str], limit: int, offset: int) -> Tuple[List[EntityModel], int]:
        """Listagem paginada - método obrigatório"""
        return await self.repo.search(q=q, limit=limit, offset=offset)
    
    async def create_entity(self, inp: CreateEntityInput) -> EntityModel:
        """Criação com validações de negócio"""
        # Validações de negócio aqui
        if await self.repo.find_by_name(inp.name):
            raise ValueError("ENTITY_ALREADY_EXISTS")
            
        # Auditoria
        entity = await self.repo.insert_entity(**inp.__dict__)
        await self.audit.write(None, "entity_created", {"entity_id": entity.id})
        return entity
```

### **Exemplo Real: Auth Service**
```python
class AuthService:
    """Exemplo do módulo auth"""
    
    def __init__(self, user_repo: UserRepo, refresh_repo: RefreshTokenRepo, ...):
        self.users = user_repo
        self.refresh = refresh_repo
        # ...
    
    async def login(self, *, login: str, senha: str, user_agent: str, client_ip: str) -> TokenBundle:
        """Lógica específica de autenticação"""
        user = await self.users.find_by_login(login)
        if not user or not self.hasher.verify(senha, user.senhaHash):
            raise AuthError("ERR_INVALID_CREDENTIALS", "Credenciais inválidas")
        
        # Gerar tokens...
        return TokenBundle(access_token=..., refresh_token=...)
```

---

## 💾 **Contrato: Repositories (Persistência)**

### **Protocol Interface**
```python
# app/services/{module}_service.py - definir protocols

class EntityRepo(Protocol):
    """Interface que todo repository deve implementar"""
    
    async def find_by_id(self, entity_id: str) -> Optional[EntityModel]:
        ...
    
    async def search(self, *, q: Optional[str], limit: int, offset: int) -> Tuple[List[EntityModel], int]:
        ...
        
    async def insert_entity(self, **fields) -> EntityModel:
        ...
        
    async def update_entity(self, entity_id: str, **fields) -> Optional[EntityModel]:
        ...
        
    async def delete_entity(self, entity_id: str) -> bool:
        ...
```

### **Implementação SQL**
```python
# app/repositories/sql_repos.py

class PgEntityRepo:
    """Implementação PostgreSQL"""
    
    def __init__(self):
        # Connection via settings ou DI
        pass
    
    async def find_by_id(self, entity_id: str) -> Optional[EntityModel]:
        """Query SQL específica"""
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM entities WHERE id = $1", 
                entity_id
            )
            return self._row_to_model(row) if row else None
    
    def _row_to_model(self, row) -> EntityModel:
        """Helper para converter row SQL -> Model"""
        return EntityModel(
            id=row["id"],
            name=row["name"],
            # ...
        )
```

### **Exemplo Real: User Repository**
```python
class PgUserRepo:
    """Repository de usuários no PostgreSQL"""
    
    async def find_by_login(self, login: str) -> Optional[UserModel]:
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE login = $1", login
            )
            return self._row_to_user_model(row) if row else None
```

---

## 🔌 **Contrato: Dependency Injection**

### **Wiring Pattern**
```python  
# app/services/{module}_wiring.py

def build_{module}_service_from_settings() -> {Module}Service:
    """Factory para criar service com todas dependências"""
    
    # Repositories
    entity_repo = PgEntityRepo()
    audit_repo = PgAuditLogRepo()
    
    # External services (se necessário)
    email_service = SMTPEmailService()
    
    # Service principal
    return EntityService(
        entity_repo=entity_repo,
        audit_repo=audit_repo,
        email_service=email_service,
    )

# Uso nos routes:
service = build_entity_service_from_settings()
```

### **Exemplo Real: Auth Wiring**
```python
def build_auth_service_from_settings() -> AuthService:
    """Factory do AuthService"""
    
    # Providers
    token_provider = RS256TokenProvider(
        iss=settings.JWT_ISS,
        private_key_pem=_read_private_key(),
        access_ttl_sec=settings.ACCESS_TTL_SEC,
    )
    hasher = PasslibHasher("bcrypt")
    
    # Repositories
    user_repo = PgUserRepo()
    refresh_repo = PgRefreshTokenRepo()
    
    return AuthService(
        user_repo=user_repo,
        refresh_repo=refresh_repo,
        hasher=hasher,
        token_provider=token_provider,
        refresh_ttl_sec=settings.REFRESH_TTL_SEC,
    )
```

---

## ❌ **Contrato: Error Handling**

### **Custom Exceptions**
```python
# app/services/{module}_service.py

class {Module}Error(Exception):
    """Exception específica do módulo"""
    
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message  
        self.details = details
        super().__init__(f"{code}: {message}")

# Uso no service:
class EntityService:
    async def create_entity(self, inp: CreateEntityInput) -> EntityModel:
        if await self.repo.find_by_name(inp.name):
            raise EntityError("ERR_NAME_EXISTS", "Nome já existe")
```

### **Error Mapping nos Routes**
```python
# app/api/{module}/routes.py

try:
    result = await service.some_operation(...)
    return result
except EntityError as e:
    # Mapping automático
    status_map = {
        "ERR_NOT_FOUND": 404,
        "ERR_ALREADY_EXISTS": 400,
        "ERR_FORBIDDEN": 403,
    }
    sc = status_map.get(e.code, 400)
    return _error_response(sc, error=e.code, message=e.message)
except Exception:
    logger.exception("operation.error") 
    return _error_response(500, error="ERR_INTERNAL", message="Erro interno")
```

### **Exemplo Real: Auth Errors**
```python
class AuthError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

# Códigos padronizados
"ERR_USER_NOT_FOUND"     → 401 
"ERR_INVALID_SENHA"      → 401
"ERR_USER_DISABLED"      → 403
"ERR_TOKEN_EXPIRED"      → 401
```

---

## 📊 **Contrato: Logging e Observabilidade**

### **Logger Pattern**
```python
# Sempre no topo do arquivo
from app.core.logging_config import get_logger
logger = get_logger("module_name")  # ou __name__
```

### **Logging Estruturado**
```python
# Padrão obrigatório: operation.{start|ok|fail}
logger.info("operation.start", extra={"entity_id": entity_id})

try:
    result = await some_operation()
    logger.info("operation.ok", extra={"entity_id": entity_id, "result_count": len(result)})
    return result
except SomeError as e:
    logger.info("operation.fail", extra={"entity_id": entity_id, "error": e.code})
    raise
except Exception:
    logger.exception("operation.error", extra={"entity_id": entity_id})
    raise
```

### **Auditoria (operações críticas)**
```python
# Para operações que mudam estado
await self.audit.write(
    user_id=current_user_id,
    event="entity_created",
    metadata={
        "entity_id": new_entity.id,
        "entity_type": "user",
        "ip": client_ip,
    }
)
```

---

## 🧪 **Contrato: Testabilidade**

### **Interface Testável**
```python
# Service aceita repositories via constructor (DI)
class EntityService:
    def __init__(self, entity_repo: EntityRepo, audit_repo: AuditLogRepo):
        self.repo = entity_repo      # Interface, não implementação
        self.audit = audit_repo
```

### **Mocks para Testes**
```python  
# tests/mocks/{module}_mocks.py

class MockEntityRepo:
    def __init__(self):
        self._entities = {}
    
    async def find_by_id(self, entity_id: str) -> Optional[EntityModel]:
        return self._entities.get(entity_id)
    
    async def insert_entity(self, **fields) -> EntityModel:
        entity = EntityModel(id=str(uuid.uuid4()), **fields)
        self._entities[entity.id] = entity
        return entity
```

---

## 🔄 **Contratos de Configuração**

### **Settings Pattern**
```python
# app/config/settings.py - adicionar configs do módulo

class Settings:
    # Configs específicas do módulo
    ENTITY_MAX_NAME_LENGTH: int = 100
    ENTITY_DEFAULT_STATUS: str = "active"
    ENTITY_CACHE_TTL_SEC: int = 300
    
    # Rate limiting 
    ENTITY_RATE_LIMIT_PER_USER: int = 100
    ENTITY_RATE_LIMIT_PER_IP: int = 1000
```

### **Environment Variables**
```bash
# .env - seguir padrão {MODULE}_{CONFIG}
ENTITY_MAX_NAME_LENGTH=100
ENTITY_DEFAULT_STATUS=active
ENTITY_CACHE_TTL_SEC=300
```

---

## 📋 **Checklist de Implementação**

Para **cada novo módulo**, implemente:

### **Camada Service**
- [ ] Models de domínio (`@dataclass`)
- [ ] Input DTOs (`CreateInput`, `UpdateInput`)  
- [ ] Service class com métodos públicos
- [ ] Custom exceptions (`{Module}Error`)
- [ ] Logging estruturado
- [ ] Auditoria (se operações críticas)

### **Camada Repository**
- [ ] Protocol interface (`{Entity}Repo`)
- [ ] Implementação SQL (`Pg{Entity}Repo`)
- [ ] Métodos obrigatórios (find_by_id, search, insert, update, delete)
- [ ] Conversão row→model (`_row_to_model`)

### **Camada API**
- [ ] Router com prefix versionado
- [ ] Endpoints CRUD padrão
- [ ] Error mapping consistente
- [ ] Dependencies apropriadas
- [ ] Response models padronizados

### **Wiring**
- [ ] Factory function (`build_{module}_service_from_settings`)
- [ ] DI de repositories
- [ ] Configuração via settings
- [ ] Instanciação no routes.py

---

## 🎯 **Exemplo Completo: Módulo Users**

### **Service Layer**
```python  
# app/services/user_service.py

@dataclass
class UserModel:
    id: str
    login: str
    nome: Optional[str]
    email: Optional[str]
    isAdmin: bool
    status: str
    createdAt: str
    updatedAt: str
    modules: Optional[List[str]]

class UserService:
    def __init__(self, user_repo: UserRepo, audit_repo: AuditLogRepo):
        self.repo = user_repo
        self.audit = audit_repo
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        return await self.repo.find_by_id(user_id)
    
    async def create_user(self, inp: CreateUserInput) -> UserModel:
        # Validação de negócio
        existing = await self.repo.find_by_login(inp.login)
        if existing:
            raise ValueError("LOGIN_ALREADY_EXISTS")
            
        # Criação
        user = await self.repo.insert_user(**inp.__dict__)
        
        # Auditoria
        await self.audit.write(None, "user_created", {"user_id": user.id})
        
        return user
```

### **Repository Layer**
```python
# app/repositories/sql_repos.py (extensão)

class PgUserRepo:
    async def find_by_id(self, user_id: str) -> Optional[UserModel]:
        async with get_conn() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            return self._row_to_user_model(row) if row else None
    
    async def find_by_login(self, login: str) -> Optional[UserModel]:
        async with get_conn() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE login = $1", login) 
            return self._row_to_user_model(row) if row else None
    
    def _row_to_user_model(self, row) -> UserModel:
        return UserModel(
            id=row["id"],
            login=row["login"],
            nome=row["nome"],
            email=row["email"], 
            isAdmin=row["is_admin"],
            status=row["status"],
            createdAt=row["created_at"].isoformat(),
            updatedAt=row["updated_at"].isoformat(),
            modules=row["modules"],
        )
```

### **API Layer**  
```python
# app/api/users/routes.py

from app.services.user_wiring import build_user_service_from_settings

router = APIRouter(prefix="/v1/users", tags=["Users"])
service = build_user_service_from_settings()

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, _: CurrentUser = Depends(require_admin)):
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail="Usuário não encontrado")
    return build_user_response(user)
```

### **Wiring Layer**
```python
# app/services/user_wiring.py

def build_user_service_from_settings() -> UserService:
    """Factory do UserService"""
    user_repo = PgUserRepo()
    audit_repo = PgAuditLogRepo()  
    
    return UserService(
        user_repo=user_repo,
        audit_repo=audit_repo,
    )
```

---

## 🎯 **Separação Auth vs Users (Caso Real)**

### **AuthService (foco: identidade)**
```python
class AuthService:
    """Responsabilidade: tokens, sessões, login"""
    
    async def login(self, login: str, senha: str) -> TokenBundle:
        # 1. Validar credenciais
        user = await self.users.find_by_login(login)  
        # 2. Gerar tokens
        # 3. Criar sessão
        return TokenBundle(access_token=jwt, user=AuthUser(...))  # dados mínimos
    
    async def refresh_token(self, refresh: str) -> TokenBundle:
        # Renovar access token
        pass
```

### **UserService (foco: dados)**
```python  
class UserService:
    """Responsabilidade: CRUD usuários, perfil"""
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        # Dados completos do usuário
        return await self.repo.find_by_id(user_id)
    
    async def update_user_profile(self, user_id: str, data: dict) -> UserModel:
        # Atualizar perfil, preferências, etc.
        pass
```

### **Comunicação Entre Módulos**
```python
# Frontend após login:
# 1. POST /v1/auth/login    → recebe tokens + AuthUser básico
# 2. GET  /v1/users/me      → recebe User completo  

# AuthService NÃO chama UserService diretamente
# Usa UserRepo compartilhado para validação mínima
```

---

## ⚡ **Performance e Caching**

### **Caching Pattern (se aplicável)**
```python
from functools import lru_cache

class EntityService:
    @lru_cache(maxsize=1000)
    async def get_entity_by_id_cached(self, entity_id: str) -> Optional[EntityModel]:
        """Cache para entidades acessadas frequentemente"""
        return await self.repo.find_by_id(entity_id)
```

### **Bulk Operations**
```python
async def bulk_create_entities(self, inputs: List[CreateEntityInput]) -> List[EntityModel]:
    """Para operações em lote quando necessário"""
    # Validação em lote
    # Insert em lote  
    # Auditoria em lote
    pass
```

---

**Próximo documento:** Templates e ferramentas de scaffolding para acelerar criação de novos módulos! 🚀