# app/api/users/schemas.py
"""
Schemas de usuários - Request/Response models.
"""
from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, constr


class CreateUserRequest(BaseModel):
    login: str
    email: Optional[str] = None
    nome: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: bool = False
    status: str = "active"
    senha: Optional[str] = Field(None, min_length=6)
    modules: Optional[List[str]] = None
    ui: Optional[dict] = None


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    nome: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: Optional[bool] = None
    status: Optional[str] = None
    modules: Optional[List[str]] = None
    ui: Optional[dict] = None


class ChangeOwnPasswordRequest(BaseModel):
    currentPassword: str
    newPassword: constr(min_length=4)



