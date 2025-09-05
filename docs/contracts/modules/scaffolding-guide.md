# 🛠️ Guia de Scaffolding e Templates

Este documento fornece **templates prontos** e **ferramentas de geração automática** para criar novos módulos seguindo todos os contratos estabelecidos.

## 🎯 **Visão Geral**

Ao invés de criar módulos manualmente, use:
1. **Templates padronizados** - código base que segue contratos
2. **Script de geração** - automatiza criação da estrutura
3. **Checklist de validação** - garante conformidade
4. **Exemplos funcionais** - referência rápida

---

## 📂 **Template: Estrutura Completa**

### **Estrutura de Arquivos Gerada**
```
app/
├── api/{module_name}/
│   ├── __init__.py           # Exports
│   ├── routes.py             # FastAPI endpoints
│   ├── schemas.py            # Pydantic models
│   └── dependencies.py       # Auth + validações [opcional]
├── services/
│   ├── {module}_service.py   # Business logic
│   └── {module}_wiring.py    # Dependency injection
├── repositories/
│   └── {module}_repos.py     # Data access [se necessário]
└── tests/
    ├── test_{module}_api.py  # Testes de API
    └── test_{module}_service.py # Testes de service
```

---

## 📄 **Template: routes.py**

```python
# app/api/{module_name}/routes.py
"""
Controller de {module_display_name} - {brief_description}.
"""
from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from app.api.auth.dependencies import require_user, require_admin, CurrentUser
from app.services.{module}_wiring import build_{module}_service_from_settings
from .schemas import (
    {Entity}, Create{Entity}Request, Update{Entity}Request,
    build_{entity}_response
)

router = APIRouter(prefix="/v1/{module_name}", tags=["{ModuleName}"])
service = build_{module}_service_from_settings()


# =========================
#   ENDPOINTS BÁSICOS
# =========================
@router.get("/{entity_id}", response_model={Entity})
async def get_{entity}(
    entity_id: str = Path(..., regex=r'^[a-zA-Z0-9_-]+$'),
    current: CurrentUser = Depends(require_user)
):
    """Busca {entity} por ID."""
    entity = await service.get_{entity}_by_id(entity_id)
    if not entity:
        raise HTTPException(404, detail="{Entity} não encontrada")
    return build_{entity}_response(entity)


@router.get("/", response_model=List[{Entity}])
async def list_{entity_plural}(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, max_length=100),
    current: CurrentUser = Depends(require_user)
):
    """Lista {entity_plural} com paginação."""
    entities, total = await service.list_{entity_plural}(q=q, limit=limit, offset=offset)
    return [build_{entity}_response(e) for e in entities]


@router.post("/", response_model={Entity}, status_code=201)
async def create_{entity}(
    body: Create{Entity}Request,
    current: CurrentUser = Depends(require_admin)  # ajustar conforme necessário
):
    """Cria nova {entity}."""
    try:
        entity = await service.create_{entity}(Create{Entity}Input(**body.dict()))
        return build_{entity}_response(entity)
    except ValueError as e:
        if str(e) == "{ENTITY}_ALREADY_EXISTS":
            raise HTTPException(400, detail="{Entity} já existe")
        raise


@router.put("/{entity_id}", response_model={Entity})
async def update_{entity}(
    entity_id: str,
    body: Update{Entity}Request,
    current: CurrentUser = Depends(require_admin)
):
    """Atualiza {entity}."""
    entity = await service.update_{entity}(entity_id, Update{Entity}Input(**body.dict()))
    if not entity:
        raise HTTPException(404, detail="{Entity} não encontrada")
    return build_{entity}_response(entity)


@router.delete("/{entity_id}", status_code=204)
async def delete_{entity}(
    entity_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Remove {entity}."""
    ok = await service.delete_{entity}(entity_id)
    if not ok:
        raise HTTPException(404, detail="{Entity} não encontrada")
    return None
```

---

## 📄 **Template: schemas.py**

```python
# app/api/{module_name}/schemas.py
"""
Schemas de {module_display_name} - Request/Response models.
"""
from __future__ import annotations

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, validator

from app.api.auth.schemas import ErrorResponse  # Reutilizar error padrão


# =========================
#   ENTITY MODEL
# =========================
class {Entity}(BaseModel):
    """Modelo completo de {entity} para responses."""
    
    # Identificação
    id: str
    name: str
    
    # Estado
    status: Literal["active", "disabled"] = "active"
    
    # Metadados
    createdAt: str
    updatedAt: str
    createdBy: Optional[str] = None
    
    # Campos específicos do módulo
    # ... adicionar conforme necessário


# =========================
#   REQUEST MODELS  
# =========================
class Create{Entity}Request(BaseModel):
    """Schema para criação de {entity}."""
    
    # Campos obrigatórios
    name: str = Field(..., min_length=2, max_length=100)
    
    # Campos opcionais
    description: Optional[str] = Field(None, max_length=500)
    status: str = Field("active", regex=r'^(active|disabled)$')
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('name')
    def validate_name(cls, v):
        """Validações específicas do módulo."""
        if not v.strip():
            raise ValueError("Nome não pode ser vazio")
        return v.strip()


class Update{Entity}Request(BaseModel):
    """Schema para atualização de {entity}."""
    
    # TODOS os campos opcionais em updates
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500) 
    status: Optional[str] = Field(None, regex=r'^(active|disabled)$')
    metadata: Optional[Dict[str, Any]] = None


# =========================
#   RESPONSE BUILDERS
# =========================
def build_{entity}_response(entity) -> {Entity}:
    """Converte model de domínio para response Pydantic."""
    return {Entity}(
        id=entity.id,
        name=entity.name,
        status=entity.status,
        createdAt=entity.createdAt,
        updatedAt=entity.updatedAt,
        createdBy=entity.createdBy,
        # ... mapear campos específicos
    )
```

---

## 📄 **Template: service.py**

```python
# app/services/{module}_service.py
"""
Service de {module_display_name} - lógica de negócio.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Protocol
import uuid

from app.core.logging_config import get_logger

logger = get_logger("services.{module}")


# =========================
#   DOMAIN MODELS
# =========================
@dataclass
class {Entity}Model:
    """Model de domínio para {entity}."""
    id: str
    name: str
    status: str
    createdAt: str
    updatedAt: str
    createdBy: Optional[str] = None


@dataclass
class Create{Entity}Input:
    """DTO para criação de {entity}."""
    name: str
    description: Optional[str] = None
    status: str = "active"
    metadata: Optional[dict] = None
    created_by: Optional[str] = None


@dataclass
class Update{Entity}Input:
    """DTO para atualização de {entity}.""" 
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


# =========================
#   REPOSITORY INTERFACE
# =========================
class {Entity}Repo(Protocol):
    """Interface do repository de {entity}."""
    
    async def find_by_id(self, entity_id: str) -> Optional[{Entity}Model]:
        ...
    
    async def search(self, *, q: Optional[str], limit: int, offset: int) -> Tuple[List[{Entity}Model], int]:
        ...
        
    async def insert_{entity}(self, **fields) -> {Entity}Model:
        ...
        
    async def update_{entity}(self, entity_id: str, **fields) -> Optional[{Entity}Model]:
        ...
        
    async def delete_{entity}(self, entity_id: str) -> bool:
        ...


class AuditLogRepo(Protocol):
    """Interface para auditoria."""
    async def write(self, user_id: Optional[str], event: str, metadata: dict) -> None:
        ...


# =========================
#   CUSTOM EXCEPTIONS
# =========================
class {Module}Error(Exception):
    """Exception específica do módulo {module}."""
    
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message  
        self.details = details
        super().__init__(f"{code}: {message}")


# =========================
#   SERVICE
# =========================
class {Module}Service:
    """Service principal do módulo {module}."""
    
    def __init__(self, {entity}_repo: {Entity}Repo, audit_repo: AuditLogRepo):
        self.repo = {entity}_repo
        self.audit = audit_repo
    
    # ---------- READ ----------
    async def get_{entity}_by_id(self, entity_id: str) -> Optional[{Entity}Model]:
        """Busca {entity} por ID."""
        logger.info("get_{entity}.start", extra={"entity_id": entity_id})
        entity = await self.repo.find_by_id(entity_id)
        
        if entity:
            logger.info("get_{entity}.ok", extra={"entity_id": entity_id})
        else:
            logger.info("get_{entity}.not_found", extra={"entity_id": entity_id})
            
        return entity
    
    async def list_{entity_plural}(
        self, *, q: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[{Entity}Model], int]:
        """Lista {entity_plural} com paginação."""
        logger.info("list_{entity_plural}.start", extra={"q": q, "limit": limit, "offset": offset})
        result = await self.repo.search(q=q, limit=limit, offset=offset)
        logger.info("list_{entity_plural}.ok", extra={"count": len(result[0])})
        return result
    
    # ---------- CREATE ----------
    async def create_{entity}(self, inp: Create{Entity}Input) -> {Entity}Model:
        """Cria nova {entity} com validações de negócio."""
        logger.info("create_{entity}.start", extra={"name": inp.name})
        
        # Validações de negócio específicas do módulo
        # Exemplo: verificar duplicatas por nome
        # existing = await self.repo.find_by_name(inp.name)
        # if existing:
        #     raise {Module}Error("ERR_{ENTITY}_ALREADY_EXISTS", "Nome já existe")
        
        # Gerar ID e timestamps
        entity_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Criar entidade
        entity = await self.repo.insert_{entity}(
            id=entity_id,
            name=inp.name,
            description=inp.description,
            status=inp.status,
            metadata=inp.metadata,
            created_by=inp.created_by,
            created_at=now,
            updated_at=now,
        )
        
        # Auditoria
        await self.audit.write(
            user_id=inp.created_by,
            event="{entity}_created", 
            metadata={"entity_id": entity.id, "entity_name": entity.name}
        )
        
        logger.info("create_{entity}.ok", extra={"entity_id": entity.id})
        return entity
    
    # ---------- UPDATE ----------
    async def update_{entity}(self, entity_id: str, inp: Update{Entity}Input) -> Optional[{Entity}Model]:
        """Atualiza {entity} existente."""
        logger.info("update_{entity}.start", extra={"entity_id": entity_id})
        
        now = datetime.now(timezone.utc).isoformat()
        
        entity = await self.repo.update_{entity}(
            entity_id=entity_id,
            name=inp.name,
            description=inp.description,
            status=inp.status,
            metadata=inp.metadata,
            updated_at=now,
        )
        
        if entity:
            await self.audit.write(
                user_id=None,  # TODO: capturar user atual
                event="{entity}_updated",
                metadata={"entity_id": entity.id}
            )
            logger.info("update_{entity}.ok", extra={"entity_id": entity_id})
        else:
            logger.info("update_{entity}.not_found", extra={"entity_id": entity_id})
            
        return entity
    
    # ---------- DELETE ----------
    async def delete_{entity}(self, entity_id: str) -> bool:
        """Remove {entity}."""
        logger.info("delete_{entity}.start", extra={"entity_id": entity_id})
        
        ok = await self.repo.delete_{entity}(entity_id)
        
        if ok:
            await self.audit.write(
                user_id=None,  # TODO: capturar user atual
                event="{entity}_deleted",
                metadata={"entity_id": entity_id}
            )
            logger.info("delete_{entity}.ok", extra={"entity_id": entity_id})
        else:
            logger.info("delete_{entity}.not_found", extra={"entity_id": entity_id})
            
        return ok
```

---

## 📄 **Template: wiring.py**

```python
# app/services/{module}_wiring.py
"""
Dependency injection para {module_display_name}.
"""
from __future__ import annotations

from app.repositories.sql_repos import Pg{Entity}Repo, PgAuditLogRepo
from .{module}_service import {Module}Service


def build_{module}_service_from_settings() -> {Module}Service:
    """
    Factory para criar {Module}Service com todas as dependências.
    """
    # Repositories
    {entity}_repo = Pg{Entity}Repo()
    audit_repo = PgAuditLogRepo()
    
    # External services (se necessário)
    # email_service = SMTPEmailService()
    # cache_service = RedisCache()
    
    return {Module}Service(
        {entity}_repo={entity}_repo,
        audit_repo=audit_repo,
    )
```

---

## 📄 **Template: __init__.py**

```python
# app/api/{module_name}/__init__.py
"""
Módulo {module_display_name}.

Responsabilidade: {brief_description}
"""

from .routes import router

__all__ = ["router"]
```

---

## 🤖 **Script de Geração Automática**

### **create_module.py**
```python
#!/usr/bin/env python3
"""
Script para gerar estrutura base de novos módulos.

Uso:
    python scripts/create_module.py products "Gestão de Produtos" "CRUD de produtos do e-commerce"
    python scripts/create_module.py notifications "Notificações" "Sistema de alertas e mensagens"
"""

import os
import sys
from pathlib import Path
from typing import Dict

def inflect_words(module_name: str) -> Dict[str, str]:
    """Gera variações da palavra para templates."""
    # Implementação simples - pode usar inflect library
    entity = module_name.rstrip('s')  # products -> product
    
    return {
        'module_name': module_name,           # products
        'module_display_name': module_name.title(),  # Products  
        'Module': module_name.title(),        # Products
        'MODULE': module_name.upper(),        # PRODUCTS
        'entity': entity,                     # product
        'Entity': entity.title(),             # Product
        'ENTITY': entity.upper(),             # PRODUCT
        'entity_plural': module_name,         # products
    }

def load_template(template_path: str, replacements: Dict[str, str]) -> str:
    """Carrega template e substitui placeholders."""
    template = Path(template_path).read_text()
    
    for key, value in replacements.items():
        template = template.replace(f'{{{key}}}', value)
        
    return template

def create_module_structure(module_name: str, module_display_name: str, brief_description: str):
    """Cria toda estrutura do módulo."""
    
    # Validações
    if not module_name.islower():
        print("❌ Nome do módulo deve ser lowercase (ex: 'products')")
        sys.exit(1)
    
    base_path = Path("app")
    if not base_path.exists():
        print("❌ Execute no root do projeto (onde está app/)")
        sys.exit(1)
    
    # Preparar substituições
    replacements = inflect_words(module_name)
    replacements['module_display_name'] = module_display_name
    replacements['brief_description'] = brief_description
    
    # Estrutura de diretórios
    dirs_to_create = [
        f"app/api/{module_name}",
        f"tests/{module_name}",
    ]
    
    # Arquivos para gerar
    files_to_create = {
        f"app/api/{module_name}/__init__.py": "templates/module/__init__.py.template",
        f"app/api/{module_name}/routes.py": "templates/module/routes.py.template", 
        f"app/api/{module_name}/schemas.py": "templates/module/schemas.py.template",
        f"app/services/{module_name}_service.py": "templates/module/service.py.template",
        f"app/services/{module_name}_wiring.py": "templates/module/wiring.py.template",
        f"tests/{module_name}/test_api.py": "templates/module/test_api.py.template",
        f"tests/{module_name}/test_service.py": "templates/module/test_service.py.template",
    }
    
    # Criar diretórios
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Criado: {dir_path}/")
    
    # Gerar arquivos
    for file_path, template_path in files_to_create.items():
        if Path(file_path).exists():
            print(f"⚠️  Já existe: {file_path} (pulando)")
            continue
            
        try:
            content = load_template(template_path, replacements)
            Path(file_path).write_text(content)
            print(f"✅ Gerado: {file_path}")
        except FileNotFoundError:
            print(f"⚠️  Template não encontrado: {template_path} (criando básico)")
            # Fallback para template inline básico
            basic_content = create_basic_template(file_path, replacements)
            Path(file_path).write_text(basic_content)
            print(f"✅ Gerado (básico): {file_path}")
    
    print(f"\n🎉 Módulo '{module_name}' criado com sucesso!")
    print("\n📋 Próximos passos:")
    print(f"1. Revisar arquivos gerados em app/api/{module_name}/")
    print(f"2. Implementar repository Pg{replacements['Entity']}Repo se necessário")
    print(f"3. Ajustar validações em schemas.py")
    print(f"4. Adicionar testes específicos")
    print(f"5. Testar endpoints: http://localhost:8000/v1/{module_name}/")

def create_basic_template(file_path: str, replacements: Dict[str, str]) -> str:
    """Cria template básico quando arquivo não existe.""" 
    if file_path.endswith('routes.py'):
        return f'''# {file_path}
from fastapi import APIRouter

router = APIRouter(prefix="/v1/{replacements['module_name']}", tags=["{replacements['Module']}"])

@router.get("/")
def list_{replacements['entity_plural']}():
    return {{"message": "TODO: Implementar listagem de {replacements['entity_plural']}"}}
'''
    elif file_path.endswith('schemas.py'):
        return f'''# {file_path}
from pydantic import BaseModel

class {replacements['Entity']}(BaseModel):
    id: str
    name: str
'''
    else:
        return f'''# {file_path}
# TODO: Implementar {replacements['module_display_name']}
'''

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python create_module.py <nome> <display_name> <descrição>")
        print("Exemplo: python create_module.py products 'Gestão de Produtos' 'CRUD de produtos'")
        sys.exit(1)
    
    module_name = sys.argv[1]
    display_name = sys.argv[2] 
    description = sys.argv[3]
    
    create_module_structure(module_name, display_name, description)
```

---

## ✅ **Checklist de Validação**

### **Após Gerar Módulo**
Execute estas verificações:

**1. Estrutura de Arquivos**
- [ ] `app/api/{module}/routes.py` existe e tem router
- [ ] `app/api/{module}/schemas.py` tem Request/Response models
- [ ] `app/services/{module}_service.py` tem service class
- [ ] `app/services/{module}_wiring.py` tem factory function
- [ ] Testes em `tests/{module}/` existem

**2. API Contracts**
- [ ] Router tem prefix `/v1/{module}`  
- [ ] Tags OpenAPI corretas
- [ ] Endpoints seguem padrão CRUD
- [ ] Error responses padronizadas
- [ ] Auth dependencies corretas

**3. Implementation Contracts** 
- [ ] Service usa dependency injection
- [ ] Repository com Protocol interface
- [ ] Custom exceptions definidas
- [ ] Logging estruturado implementado
- [ ] Auditoria para operações críticas

**4. Funcionalidade**
- [ ] `uvicorn app.main:app --reload` inicia sem erros
- [ ] Endpoints aparecem em `/docs` (Swagger)
- [ ] Testes unitários passam
- [ ] Linting (black, flake8, mypy) sem erros

---

## 🚀 **Exemplos de Uso**

### **Criar Módulo de Produtos**
```bash
python scripts/create_module.py products "Gestão de Produtos" "CRUD produtos e-commerce"
```

**Gera:**
- `/v1/products/` - listagem  
- `/v1/products/{id}` - detalhes
- `/v1/products/` (POST) - criação
- `ProductService`, `ProductModel`, schemas, etc.

### **Criar Módulo de Notificações**
```bash  
python scripts/create_module.py notifications "Sistema de Notificações" "Alertas e mensagens"
```

**Gera:**
- `/v1/notifications/` - listar notificações
- `/v1/notifications/{id}/mark-read` - ação específica  
- `NotificationService`, streaming SSE, etc.

---

## 🎯 **Templates Especializados**

### **Para Módulos Simples (só CRUD)**
Use o template padrão acima.

### **Para Módulos com IA/Processamento**
```python
# Adicionar aos routes.py:

@router.post("/{entity_id}/process")
async def process_entity(
    entity_id: str,
    current: CurrentUser = Depends(require_user)
):
    """Processar {entity} com IA."""
    return StreamingResponse(
        service.process_with_ai(entity_id),
        media_type="text/event-stream"
    )
```

### **Para Módulos com Upload** 
```python
# Adicionar aos routes.py:

@router.post("/{entity_id}/upload")
async def upload_file(
    entity_id: str,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_user)
):
    """Upload arquivo para {entity}."""
    result = await service.process_upload(entity_id, file)
    return {"message": "Upload concluído", "file_id": result.id}
```

---

## 📚 **Referências Rápidas**

### **Comandos Úteis**
```bash
# Gerar novo módulo
python scripts/create_module.py {name} "{Display Name}" "{Description}"

# Validar estrutura  
python scripts/validate_module.py {module_name}

# Executar testes do módulo
pytest tests/{module_name}/ -v

# Verificar conformidade
python scripts/check_contracts.py {module_name}
```

### **Links para Documentação**
- [📋 Contratos de Interface](./interface-contracts.md)
- [🌐 Contratos de API](./api-contracts.md)  
- [⚙️ Contratos de Implementação](./implementation-contracts.md)
- [📖 Módulos Existentes](../../../modules/) - para referência

---

**🎉 Com estes templates, criar um novo módulo leva apenas 5 minutos e garante total conformidade com os contratos estabelecidos!**