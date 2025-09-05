#!/usr/bin/env python3
"""
Script para gerar estrutura base de novos módulos seguindo contratos estabelecidos.

Uso:
    python scripts/create_module.py products "Gestão de Produtos" "CRUD de produtos do e-commerce"
    python scripts/create_module.py notifications "Notificações" "Sistema de alertas e mensagens"
    
Gera automaticamente:
    - Estrutura de arquivos (routes, schemas, service, wiring)
    - Templates com código funcional
    - Testes básicos
    - Conformidade com contratos
"""

import os
import sys
from pathlib import Path
from typing import Dict
import argparse


def inflect_words(module_name: str) -> Dict[str, str]:
    """Gera variações da palavra para substituição nos templates."""
    
    # Lógica simples de singularização (pode ser melhorada com biblioteca inflect)
    if module_name.endswith('ies'):
        entity = module_name[:-3] + 'y'  # companies -> company
    elif module_name.endswith('s'):
        entity = module_name[:-1]        # products -> product
    else:
        entity = module_name             # user -> user
    
    return {
        'module_name': module_name,                    # products
        'module_display_name': '',                     # será preenchido
        'brief_description': '',                       # será preenchido
        'Module': module_name.title(),                 # Products
        'MODULE': module_name.upper(),                 # PRODUCTS
        'entity': entity,                              # product
        'Entity': entity.title(),                      # Product
        'ENTITY': entity.upper(),                      # PRODUCT
        'entity_plural': module_name,                  # products
    }


def create_routes_template(replacements: Dict[str, str]) -> str:
    """Template para routes.py."""
    return f'''# app/api/{replacements['module_name']}/routes.py
"""
Controller de {replacements['module_display_name']} - {replacements['brief_description']}.
"""
from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from app.api.auth.dependencies import require_user, require_admin, CurrentUser
from app.services.{replacements['module_name']}_wiring import build_{replacements['module_name']}_service_from_settings
from .schemas import (
    {replacements['Entity']}, Create{replacements['Entity']}Request, Update{replacements['Entity']}Request,
    build_{replacements['entity']}_response
)

router = APIRouter(prefix="/v1/{replacements['module_name']}", tags=["{replacements['Module']}"])
service = build_{replacements['module_name']}_service_from_settings()


# =========================
#   ENDPOINTS BÁSICOS
# =========================
@router.get("/{{entity_id}}", response_model={replacements['Entity']})
async def get_{replacements['entity']}(
    entity_id: str = Path(..., regex=r'^[a-zA-Z0-9_-]+$'),
    current: CurrentUser = Depends(require_user)
):
    """Busca {replacements['entity']} por ID."""
    entity = await service.get_{replacements['entity']}_by_id(entity_id)
    if not entity:
        raise HTTPException(404, detail="{replacements['Entity']} não encontrada")
    return build_{replacements['entity']}_response(entity)


@router.get("/", response_model=List[{replacements['Entity']}])
async def list_{replacements['entity_plural']}(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, max_length=100),
    current: CurrentUser = Depends(require_user)
):
    """Lista {replacements['entity_plural']} com paginação."""
    entities, total = await service.list_{replacements['entity_plural']}(q=q, limit=limit, offset=offset)
    return [build_{replacements['entity']}_response(e) for e in entities]


@router.post("/", response_model={replacements['Entity']}, status_code=201)
async def create_{replacements['entity']}(
    body: Create{replacements['Entity']}Request,
    current: CurrentUser = Depends(require_admin)  # ajustar conforme necessário
):
    """Cria nova {replacements['entity']}."""
    try:
        entity = await service.create_{replacements['entity']}(body)
        return build_{replacements['entity']}_response(entity)
    except ValueError as e:
        if str(e) == "{replacements['ENTITY']}_ALREADY_EXISTS":
            raise HTTPException(400, detail="{replacements['Entity']} já existe")
        raise


@router.put("/{{entity_id}}", response_model={replacements['Entity']})
async def update_{replacements['entity']}(
    entity_id: str,
    body: Update{replacements['Entity']}Request,
    current: CurrentUser = Depends(require_admin)
):
    """Atualiza {replacements['entity']}."""
    entity = await service.update_{replacements['entity']}(entity_id, body)
    if not entity:
        raise HTTPException(404, detail="{replacements['Entity']} não encontrada")
    return build_{replacements['entity']}_response(entity)


@router.delete("/{{entity_id}}", status_code=204)
async def delete_{replacements['entity']}(
    entity_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Remove {replacements['entity']}."""
    ok = await service.delete_{replacements['entity']}(entity_id)
    if not ok:
        raise HTTPException(404, detail="{replacements['Entity']} não encontrada")
    return None
'''


def create_schemas_template(replacements: Dict[str, str]) -> str:
    """Template para schemas.py."""
    return f'''# app/api/{replacements['module_name']}/schemas.py
"""
Schemas de {replacements['module_display_name']} - Request/Response models.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.api.auth.schemas import ErrorResponse  # Reutilizar error padrão


# =========================
#   ENTITY MODEL
# =========================
class {replacements['Entity']}(BaseModel):
    """Modelo completo de {replacements['entity']} para responses."""
    
    # Identificação
    id: str
    name: str
    
    # Estado
    status: str = "active"
    description: Optional[str] = None
    
    # Metadados
    createdAt: str
    updatedAt: str
    createdBy: Optional[str] = None
    
    # TODO: Adicionar campos específicos do módulo


# =========================
#   REQUEST MODELS  
# =========================
class Create{replacements['Entity']}Request(BaseModel):
    """Schema para criação de {replacements['entity']}."""
    
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


class Update{replacements['Entity']}Request(BaseModel):
    """Schema para atualização de {replacements['entity']}."""
    
    # TODOS os campos opcionais em updates
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500) 
    status: Optional[str] = Field(None, regex=r'^(active|disabled)$')
    metadata: Optional[Dict[str, Any]] = None


# =========================
#   RESPONSE BUILDERS
# =========================
def build_{replacements['entity']}_response(entity) -> {replacements['Entity']}:
    """Converte model de domínio para response Pydantic."""
    return {replacements['Entity']}(
        id=entity.id,
        name=entity.name,
        status=entity.status,
        description=getattr(entity, 'description', None),
        createdAt=entity.createdAt,
        updatedAt=entity.updatedAt,
        createdBy=getattr(entity, 'createdBy', None),
    )
'''


def create_service_template(replacements: Dict[str, str]) -> str:
    """Template para service.py."""
    return f'''# app/services/{replacements['module_name']}_service.py
"""
Service de {replacements['module_display_name']} - lógica de negócio.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Protocol
import uuid

from app.core.logging_config import get_logger

logger = get_logger("services.{replacements['module_name']}")


# =========================
#   DOMAIN MODELS
# =========================
@dataclass
class {replacements['Entity']}Model:
    """Model de domínio para {replacements['entity']}."""
    id: str
    name: str
    status: str
    description: Optional[str] = None
    createdAt: str
    updatedAt: str
    createdBy: Optional[str] = None


@dataclass
class Create{replacements['Entity']}Input:
    """DTO para criação de {replacements['entity']}."""
    name: str
    description: Optional[str] = None
    status: str = "active"
    metadata: Optional[dict] = None
    created_by: Optional[str] = None


@dataclass
class Update{replacements['Entity']}Input:
    """DTO para atualização de {replacements['entity']}.""" 
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


# =========================
#   REPOSITORY INTERFACE
# =========================
class {replacements['Entity']}Repo(Protocol):
    """Interface do repository de {replacements['entity']}."""
    
    async def find_by_id(self, entity_id: str) -> Optional[{replacements['Entity']}Model]:
        ...
    
    async def search(self, *, q: Optional[str], limit: int, offset: int) -> Tuple[List[{replacements['Entity']}Model], int]:
        ...
        
    async def insert_{replacements['entity']}(self, **fields) -> {replacements['Entity']}Model:
        ...
        
    async def update_{replacements['entity']}(self, entity_id: str, **fields) -> Optional[{replacements['Entity']}Model]:
        ...
        
    async def delete_{replacements['entity']}(self, entity_id: str) -> bool:
        ...


class AuditLogRepo(Protocol):
    """Interface para auditoria."""
    async def write(self, user_id: Optional[str], event: str, metadata: dict) -> None:
        ...


# =========================
#   CUSTOM EXCEPTIONS
# =========================
class {replacements['Module']}Error(Exception):
    """Exception específica do módulo {replacements['module_name']}."""
    
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message  
        self.details = details
        super().__init__(f"{{code}}: {{message}}")


# =========================
#   SERVICE
# =========================
class {replacements['Module']}Service:
    """Service principal do módulo {replacements['module_name']}."""
    
    def __init__(self, {replacements['entity']}_repo: {replacements['Entity']}Repo, audit_repo: AuditLogRepo):
        self.repo = {replacements['entity']}_repo
        self.audit = audit_repo
    
    # ---------- READ ----------
    async def get_{replacements['entity']}_by_id(self, entity_id: str) -> Optional[{replacements['Entity']}Model]:
        """Busca {replacements['entity']} por ID."""
        logger.info("get_{replacements['entity']}.start", extra={{"entity_id": entity_id}})
        entity = await self.repo.find_by_id(entity_id)
        
        if entity:
            logger.info("get_{replacements['entity']}.ok", extra={{"entity_id": entity_id}})
        else:
            logger.info("get_{replacements['entity']}.not_found", extra={{"entity_id": entity_id}})
            
        return entity
    
    async def list_{replacements['entity_plural']}(
        self, *, q: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[{replacements['Entity']}Model], int]:
        """Lista {replacements['entity_plural']} com paginação."""
        logger.info("list_{replacements['entity_plural']}.start", extra={{"q": q, "limit": limit, "offset": offset}})
        result = await self.repo.search(q=q, limit=limit, offset=offset)
        logger.info("list_{replacements['entity_plural']}.ok", extra={{"count": len(result[0])}})
        return result
    
    # ---------- CREATE ----------
    async def create_{replacements['entity']}(self, inp: Create{replacements['Entity']}Input) -> {replacements['Entity']}Model:
        """Cria nova {replacements['entity']} com validações de negócio."""
        logger.info("create_{replacements['entity']}.start", extra={{"name": inp.name}})
        
        # TODO: Implementar validações específicas do módulo
        # Exemplo: verificar duplicatas por nome
        # existing = await self.repo.find_by_name(inp.name)
        # if existing:
        #     raise {replacements['Module']}Error("ERR_{replacements['ENTITY']}_ALREADY_EXISTS", "Nome já existe")
        
        # Gerar ID e timestamps
        entity_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Criar entidade
        entity = await self.repo.insert_{replacements['entity']}(
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
            event="{replacements['entity']}_created", 
            metadata={{"entity_id": entity.id, "entity_name": entity.name}}
        )
        
        logger.info("create_{replacements['entity']}.ok", extra={{"entity_id": entity.id}})
        return entity
    
    # ---------- UPDATE ----------
    async def update_{replacements['entity']}(self, entity_id: str, inp: Update{replacements['Entity']}Input) -> Optional[{replacements['Entity']}Model]:
        """Atualiza {replacements['entity']} existente."""
        logger.info("update_{replacements['entity']}.start", extra={{"entity_id": entity_id}})
        
        now = datetime.now(timezone.utc).isoformat()
        
        entity = await self.repo.update_{replacements['entity']}(
            entity_id=entity_id,
            name=inp.name,
            description=inp.description,
            status=inp.status,
            metadata=inp.metadata,
            updated_at=now,
        )
        
        if entity:
            await self.audit.write(
                user_id=None,  # TODO: capturar user atual do contexto
                event="{replacements['entity']}_updated",
                metadata={{"entity_id": entity.id}}
            )
            logger.info("update_{replacements['entity']}.ok", extra={{"entity_id": entity_id}})
        else:
            logger.info("update_{replacements['entity']}.not_found", extra={{"entity_id": entity_id}})
            
        return entity
    
    # ---------- DELETE ----------
    async def delete_{replacements['entity']}(self, entity_id: str) -> bool:
        """Remove {replacements['entity']}."""
        logger.info("delete_{replacements['entity']}.start", extra={{"entity_id": entity_id}})
        
        ok = await self.repo.delete_{replacements['entity']}(entity_id)
        
        if ok:
            await self.audit.write(
                user_id=None,  # TODO: capturar user atual do contexto
                event="{replacements['entity']}_deleted",
                metadata={{"entity_id": entity_id}}
            )
            logger.info("delete_{replacements['entity']}.ok", extra={{"entity_id": entity_id}})
        else:
            logger.info("delete_{replacements['entity']}.not_found", extra={{"entity_id": entity_id}})
            
        return ok
'''


def create_wiring_template(replacements: Dict[str, str]) -> str:
    """Template para wiring.py."""
    return f'''# app/services/{replacements['module_name']}_wiring.py
"""
Dependency injection para {replacements['module_display_name']}.
"""
from __future__ import annotations

# from app.repositories.sql_repos import Pg{replacements['Entity']}Repo, PgAuditLogRepo
from app.repositories.sql_repos import PgAuditLogRepo
from .{replacements['module_name']}_service import {replacements['Module']}Service


# TODO: Implementar Pg{replacements['Entity']}Repo em app/repositories/sql_repos.py
class Mock{replacements['Entity']}Repo:
    """Repository mock temporário."""
    
    def __init__(self):
        self._entities = {{}}
    
    async def find_by_id(self, entity_id: str):
        return self._entities.get(entity_id)
    
    async def search(self, *, q, limit, offset):
        items = list(self._entities.values())
        return items[offset:offset+limit], len(items)
    
    async def insert_{replacements['entity']}(self, **fields):
        from .{replacements['module_name']}_service import {replacements['Entity']}Model
        entity = {replacements['Entity']}Model(**fields)
        self._entities[entity.id] = entity
        return entity
    
    async def update_{replacements['entity']}(self, entity_id: str, **fields):
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            for key, value in fields.items():
                if value is not None:
                    setattr(entity, key, value)
            return entity
        return None
    
    async def delete_{replacements['entity']}(self, entity_id: str):
        return self._entities.pop(entity_id, None) is not None


def build_{replacements['module_name']}_service_from_settings() -> {replacements['Module']}Service:
    """
    Factory para criar {replacements['Module']}Service com todas as dependências.
    """
    # TODO: Trocar por Pg{replacements['Entity']}Repo quando implementado
    {replacements['entity']}_repo = Mock{replacements['Entity']}Repo()
    audit_repo = PgAuditLogRepo()
    
    # External services (se necessário)
    # email_service = SMTPEmailService()
    # cache_service = RedisCache()
    
    return {replacements['Module']}Service(
        {replacements['entity']}_repo={replacements['entity']}_repo,
        audit_repo=audit_repo,
    )
'''


def create_init_template(replacements: Dict[str, str]) -> str:
    """Template para __init__.py."""
    return f'''# app/api/{replacements['module_name']}/__init__.py
"""
Módulo {replacements['module_display_name']}.

Responsabilidade: {replacements['brief_description']}
"""

from .routes import router

__all__ = ["router"]
'''


def create_test_api_template(replacements: Dict[str, str]) -> str:
    """Template para test_api.py."""
    return f'''# tests/{replacements['module_name']}/test_api.py
"""
Testes de API para módulo {replacements['module_name']}.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestModule{replacements['Module']}API:
    """Testes dos endpoints de {replacements['module_name']}."""
    
    def test_list_{replacements['entity_plural']}(self):
        """Testa listagem de {replacements['entity_plural']}."""
        # TODO: Implementar teste
        response = client.get("/v1/{replacements['module_name']}/")
        # assert response.status_code == 200
        pass
    
    def test_get_{replacements['entity']}(self):
        """Testa busca de {replacements['entity']} por ID.""" 
        # TODO: Implementar teste
        pass
    
    def test_create_{replacements['entity']}(self):
        """Testa criação de {replacements['entity']}."""
        # TODO: Implementar teste
        pass
    
    def test_update_{replacements['entity']}(self):
        """Testa atualização de {replacements['entity']}."""
        # TODO: Implementar teste
        pass
        
    def test_delete_{replacements['entity']}(self):
        """Testa remoção de {replacements['entity']}."""
        # TODO: Implementar teste  
        pass
'''


def create_module_structure(module_name: str, module_display_name: str, brief_description: str):
    """Cria toda estrutura do módulo."""
    
    # Validações de entrada
    if not module_name.islower():
        print("❌ Nome do módulo deve ser lowercase (ex: 'products')")
        sys.exit(1)
    
    if not module_name.replace('_', '').isalnum():
        print("❌ Nome do módulo deve conter apenas letras, números e underscore")
        sys.exit(1)
    
    base_path = Path("app")
    if not base_path.exists():
        print("❌ Execute este script no root do projeto (onde está app/)")
        sys.exit(1)
    
    # Verificar se módulo já existe
    module_path = Path(f"app/app/api/{module_name}")
    if module_path.exists():
        print(f"❌ Módulo '{module_name}' já existe em {module_path}")
        sys.exit(1)
    
    # Preparar substituições
    replacements = inflect_words(module_name)
    replacements['module_display_name'] = module_display_name
    replacements['brief_description'] = brief_description
    
    print(f"🚀 Criando módulo '{module_name}'...")
    print(f"   Display Name: {module_display_name}")
    print(f"   Descrição: {brief_description}")
    print()
    
    # Estrutura de diretórios
    dirs_to_create = [
        f"app/app/api/{module_name}",
        f"tests/{module_name}",
    ]
    
    # Criar diretórios
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Criado: {dir_path}/")
    
    # Templates para gerar
    templates = {
        f"app/app/api/{module_name}/__init__.py": create_init_template(replacements),
        f"app/app/api/{module_name}/routes.py": create_routes_template(replacements),
        f"app/app/api/{module_name}/schemas.py": create_schemas_template(replacements),
        f"app/app/services/{module_name}_service.py": create_service_template(replacements),
        f"app/app/services/{module_name}_wiring.py": create_wiring_template(replacements),
        f"tests/{module_name}/test_api.py": create_test_api_template(replacements),
    }
    
    # Gerar arquivos
    for file_path, content in templates.items():
        if Path(file_path).exists():
            print(f"⚠️  Já existe: {file_path} (pulando)")
            continue
            
        Path(file_path).write_text(content)
        print(f"📄 Gerado: {file_path}")
    
    print(f"\n🎉 Módulo '{module_name}' criado com sucesso!")
    print("\n📋 Próximos passos:")
    print(f"1. 📝 Revisar e customizar arquivos em app/api/{module_name}/")
    print(f"2. 🗄️  Implementar Pg{replacements['Entity']}Repo em app/repositories/sql_repos.py")
    print(f"3. ⚙️  Ajustar validações específicas em schemas.py")
    print(f"4. 🧪 Implementar testes em tests/{module_name}/")
    print(f"5. 🌐 Testar endpoints: http://localhost:8000/v1/{module_name}/")
    print(f"6. 📖 Ver docs: http://localhost:8000/docs")
    
    print(f"\n🛠️  TODO items gerados:")
    print(f"- [ ] Implementar validações de negócio em {replacements['Module']}Service")
    print(f"- [ ] Criar tabela e repository Pg{replacements['Entity']}Repo") 
    print(f"- [ ] Adicionar campos específicos do módulo")
    print(f"- [ ] Escrever testes unitários")
    print(f"- [ ] Configurar rate limiting se necessário")
    print(f"- [ ] Documentar APIs específicas")


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Gera estrutura completa de novo módulo seguindo contratos estabelecidos."
    )
    parser.add_argument("module_name", help="Nome do módulo (lowercase, ex: products)")
    parser.add_argument("display_name", help="Nome para exibição (ex: 'Gestão de Produtos')")
    parser.add_argument("description", help="Descrição breve (ex: 'CRUD de produtos do e-commerce')")
    
    args = parser.parse_args()
    
    create_module_structure(
        module_name=args.module_name,
        module_display_name=args.display_name, 
        brief_description=args.description
    )


if __name__ == "__main__":
    main()