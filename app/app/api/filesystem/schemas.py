# app/api/filesystem/schemas.py
"""
Schemas para operações de sistema de arquivos.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# =========================
#   REQUEST SCHEMAS
# =========================
class FileWriteRequest(BaseModel):
    path: str = Field(..., description="Caminho relativo ao APP_ROOT")
    content: str = Field(..., description="Conteúdo do arquivo")
    encoding: str = Field("text", description="'text' ou 'base64'")
    append: bool = Field(False, description="Se True, adiciona ao final do arquivo")
    make_dirs: bool = Field(True, description="Criar diretórios pais se necessário")
    backup: bool = Field(False, description="Criar backup antes de sobrescrever")
    chmod: Optional[str] = Field(None, description="Permissões (ex.: '0644')")
    max_bytes: int = Field(5_000_000, ge=1, le=50_000_000, description="Limite de tamanho")


class MkdirRequest(BaseModel):
    path: str = Field(..., description="Caminho relativo ao APP_ROOT")
    parents: bool = Field(True, description="Criar diretórios pais se necessário")
    exist_ok: bool = Field(True, description="Não falhar se diretório já existe")


class DeleteRequest(BaseModel):
    path: str = Field(..., description="Caminho relativo ao APP_ROOT")
    recursive: bool = Field(False, description="Remover recursivamente (diretórios)")


class MoveRequest(BaseModel):
    source: str = Field(..., description="Caminho origem (relativo ao APP_ROOT)")
    destination: str = Field(..., description="Caminho destino (relativo ao APP_ROOT)")


class CopyRequest(BaseModel):
    source: str = Field(..., description="Caminho origem (relativo ao APP_ROOT)")
    destination: str = Field(..., description="Caminho destino (relativo ao APP_ROOT)")
    recursive: bool = Field(False, description="Copiar recursivamente (diretórios)")


class TouchRequest(BaseModel):
    path: str = Field(..., description="Caminho relativo ao APP_ROOT")
    make_dirs: bool = Field(True, description="Criar diretórios pais se necessário")


# =========================
#   RESPONSE SCHEMAS
# =========================
class DirectoryListing(BaseModel):
    path: str
    files: List[str]
    directories: List[str]
    total_files: int
    total_dirs: int


class FileContent(BaseModel):
    path: str
    size: int
    mime: str
    is_text: bool
    truncated: bool
    encoding: str
    content: str


class FileOperationResult(BaseModel):
    path: str
    success: bool
    message: Optional[str] = None
    details: Optional[Dict] = None


class TreeItem(BaseModel):
    name: str
    type: str  # "file" ou "directory"
    size: Optional[int] = None
    children: Optional[List["TreeItem"]] = None


class DirectoryTree(BaseModel):
    path: str
    depth: int
    items: List[TreeItem]
    total_items: int


