# 🌐 Contratos de API para Módulos

Este documento define os **contratos obrigatórios de API** que todos os módulos devem implementar.

## 🎯 **Convenções Gerais**

### **1. Versionamento**
```python
# OBRIGATÓRIO: Todos os endpoints devem ser versionados
router = APIRouter(prefix="/v1/{module_name}", tags=["{ModuleName}"])

# ✅ Exemplos corretos:
# /v1/auth/login
# /v1/users/me  
# /v1/agents/chat
# /v1/workspace/projects

# ❌ Incorreto:
# /auth/login         (sem versão)
# /api/v1/users       (redundante)
```

### **2. Tags OpenAPI**
```python
# Use o nome do módulo em PascalCase
tags=["Authentication"]  # para auth
tags=["Users"]          # para users  
tags=["Agents"]         # para agents
tags=["Workspace"]      # para workspace
```

---

## 📋 **Padrões de Endpoints**

### **1. Operações CRUD (se aplicável)**

**Listagem com Paginação**
```python
@router.get("/", response_model=List[EntityResponse])
async def list_entities(
    # Paginação obrigatória
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    
    # Busca opcional
    q: Optional[str] = Query(None, max_length=100),
    
    # Filtros específicos do módulo
    status: Optional[str] = Query(None),
    
    # Auth conforme necessário
    current: CurrentUser = Depends(require_user)  # ou require_admin
):
    entities, total = await service.list_entities(q=q, limit=limit, offset=offset)
    return [build_entity_response(e) for e in entities]
```

**Busca Individual**
```python
@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str = Path(..., regex=r'^[a-zA-Z0-9_-]+$'),
    current: CurrentUser = Depends(require_user)
):
    entity = await service.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(404, detail="Entity não encontrada")
    return build_entity_response(entity)
```

**Criação**
```python
@router.post("/", response_model=EntityResponse, status_code=201)
async def create_entity(
    body: CreateEntityRequest,
    current: CurrentUser = Depends(require_admin)  # ou require_user
):
    try:
        entity = await service.create_entity(CreateEntityInput(**body.dict()))
        return build_entity_response(entity)
    except ValueError as e:
        # Mapeamento de erros de negócio
        if str(e) == "ENTITY_ALREADY_EXISTS":
            raise HTTPException(400, detail="Entity já existe")
        raise
```

**Atualização**
```python
@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: str,
    body: UpdateEntityRequest, 
    current: CurrentUser = Depends(require_admin)
):
    entity = await service.update_entity(entity_id, UpdateEntityInput(**body.dict()))
    if not entity:
        raise HTTPException(404, detail="Entity não encontrada")
    return build_entity_response(entity)
```

**Remoção**
```python
@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: str,
    current: CurrentUser = Depends(require_admin)
):
    ok = await service.delete_entity(entity_id)
    if not ok:
        raise HTTPException(404, detail="Entity não encontrada")
    # Retorno vazio para 204
    return None
```

### **2. Endpoints Especiais**

**Dados do Próprio Usuário**
```python
@router.get("/me", response_model=EntityResponse)
async def get_my_entity(current: CurrentUser = Depends(require_user)):
    """Padrão para dados do usuário autenticado"""
    entity = await service.get_entity_by_user_id(current["sub"])
    if not entity:
        raise HTTPException(404, detail="Entity não encontrada")
    return build_entity_response(entity)
```

**Ações Específicas**
```python
@router.post("/{entity_id}/action", status_code=200)
async def perform_action(
    entity_id: str,
    body: ActionRequest,
    current: CurrentUser = Depends(require_user)
):
    """Ações específicas do módulo (ex: /users/{id}/reset-password)"""
    result = await service.perform_action(entity_id, action_data=body.dict())
    return {"message": "Ação executada com sucesso"}
```

---

## 📨 **Contratos de Request/Response**

### **1. Headers Obrigatórios**

**Para Autenticação**
```python
# JWT (UI/Frontend)
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...

# API Key (microserviços internos)  
X-API-Key: your-secret-api-key

# Para debugging (opcional)
X-Trace-ID: uuid-v4-trace-id
```

**Para Upload (se aplicável)**
```python
Content-Type: multipart/form-data
Content-Length: 1024
```

### **2. Query Parameters**

**Paginação (obrigatória em listagens)**
```python
# Page-based (preferido para UIs)
?page=1&pageSize=20

# Cursor-based (preferido para APIs)  
?cursor=eyJpZCI6IjEyMyJ9&limit=50

# Offset-based (fallback)
?limit=50&offset=100
```

**Filtros e Busca**
```python
# Busca textual
?q=termo+busca

# Filtros por status
?status=active&status=pending  # array

# Ordenação
?sort=createdAt&order=desc
```

### **3. Request Body**

**JSON (padrão)**
```python
Content-Type: application/json

{
  "name": "Entity Name",
  "description": "Optional description", 
  "metadata": {"key": "value"}
}
```

**Multipart (uploads)**
```python
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="document.pdf"
Content-Type: application/pdf

[binary data]
--boundary--
```

---

## 📤 **Contratos de Response**

### **1. Success Responses**

**200 OK - Dados únicos**
```json
{
  "id": "user123",
  "name": "João Silva",
  "status": "active",
  "createdAt": "2024-01-15T10:30:00Z"
}
```

**200 OK - Listagem com Metadata**
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "pageSize": 20,  
    "total": 156,
    "totalPages": 8
  }
}
```

**201 Created**
```json
{
  "id": "newly-created-id",
  "name": "Entity Name", 
  "status": "active",
  "createdAt": "2024-01-15T10:30:00Z"
}
```

**204 No Content**
```
# Corpo vazio para DELETE, PUT sem retorno
```

### **2. Error Responses (padronizado)**

**400 Bad Request**
```json
{
  "error": "ERR_INVALID_INPUT",
  "message": "Campo 'email' é obrigatório",
  "details": {
    "field": "email",
    "constraint": "required"
  }
}
```

**401 Unauthorized** 
```json
{
  "error": "ERR_TOKEN_EXPIRED", 
  "message": "Token JWT expirado",
  "traceId": "abc-123-def"
}
```

**403 Forbidden**
```json
{
  "error": "ERR_INSUFFICIENT_PERMISSIONS",
  "message": "Operação requer privilégios de admin"
}
```

**404 Not Found**
```json  
{
  "error": "ERR_USER_NOT_FOUND",
  "message": "Usuário com ID 'user123' não encontrado"
}
```

**500 Internal Server Error**
```json
{
  "error": "ERR_INTERNAL", 
  "message": "Erro interno do servidor",
  "traceId": "abc-123-def"
}
```

---

## 🕒 **Contratos de Performance**

### **1. Timeouts**
```python
# Por tipo de operação
CRUD_TIMEOUT = 5000      # ms - operações simples
SEARCH_TIMEOUT = 10000   # ms - buscas complexas  
AI_TIMEOUT = 30000       # ms - processamento IA
UPLOAD_TIMEOUT = 60000   # ms - uploads grandes
```

### **2. Rate Limiting**
```python
# Por tipo de usuário
USER_RATE_LIMIT = 100    # req/min usuário comum
ADMIN_RATE_LIMIT = 500   # req/min admin
API_RATE_LIMIT = 1000    # req/min microserviços
```

### **3. Payload Limits**
```python
# Por tipo de conteúdo
JSON_MAX_SIZE = "1MB"    # requests JSON
UPLOAD_MAX_SIZE = "10MB" # uploads de arquivo
SEARCH_MAX_RESULTS = 1000 # resultados de busca
```

---

## 🔄 **Contratos de Streaming**

### **Server-Sent Events (SSE)**
```python
@router.get("/stream", dependencies=[Depends(require_user)])
async def stream_data():
    """Para dados em tempo real"""
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

# Formato dos eventos
data: {"type": "progress", "data": {"percentage": 25}}
data: {"type": "result", "data": {"id": "123", "status": "completed"}}
```

### **NDJSON (Newline Delimited JSON)**
```python
@router.post("/bulk-process", dependencies=[Depends(require_user)])  
async def bulk_process():
    """Para processamento em lotes"""
    return StreamingResponse(
        process_items(),
        media_type="application/x-ndjson"
    )

# Formato: uma linha JSON por resultado
{"id": "1", "status": "processed", "result": {...}}
{"id": "2", "status": "error", "error": "ERR_INVALID_DATA"}
```

---

## 🎯 **Aplicação Prática: Auth vs Users**

### **Módulo Auth (responsabilidade: identidade)**
```python
# ✅ Correto - foca só em autenticação
POST /v1/auth/login       → LoginResponse + AuthUser mínimo
POST /v1/auth/refresh     → RefreshResponse  
POST /v1/auth/logout      → LogoutResponse
```

### **Módulo Users (responsabilidade: dados)**
```python  
# ✅ Correto - foca em gestão de dados
GET  /v1/users/me         → User completo
GET  /v1/users/           → List[User] (admin)
POST /v1/users/           → User (admin)
PUT  /v1/users/{id}       → User (admin)
```

### **Comunicação Entre Módulos**
```python
# Frontend faz 2 calls após login:
1. POST /v1/auth/login    # obtém tokens + dados básicos
2. GET  /v1/users/me      # obtém perfil completo

# Microserviços usam API Key:
GET /v1/users/{id}        # com X-API-Key header
```

Pronto! 🎉 Criamos o **primeiro documento de contratos**. Ele estabelece as **regras fundamentais** que todos os módulos devem seguir.

**Esta estrutura funciona como base para:**
1. ✅ **Review de módulos existentes** - verificar conformidade
2. ✅ **Criação de novos módulos** - seguir os padrões  
3. ✅ **Onboarding de devs** - entender rapidamente as regras
4. ✅ **Refactoring** - exemplo prático com auth/users

**Próximo passo:** Quer que eu continue com os **Contratos de Implementação** (services, repositories, wiring) ou prefere ajustar algo neste documento primeiro?