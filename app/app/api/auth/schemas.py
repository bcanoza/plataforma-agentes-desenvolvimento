# app/api/auth/schemas.py
"""
Schemas de autenticação - Request/Response models.
Consolidados de auth_ui_controller.py e auth_controller.py
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal, Any, Dict

from pydantic import BaseModel, constr, Field


# =========================
#   SCHEMAS DE USUÁRIO
# =========================
class Preferences(BaseModel):
    themePreferred: Optional[Literal["vscode", "light", "dark"]] = None
    moduleOrder: Optional[List[str]] = None
    iconOrder: Optional[List[str]] = None


class User(BaseModel):
    id: str
    login: str
    nome: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: bool
    status: Literal["active", "disabled"]
    senhaHash: Optional[str] = Field(default=None, exclude=True)
    senhaUpdatedAt: Optional[str] = Field(default=None, exclude=True)
    lastLoginAt: Optional[str] = None
    lastLoginIp: Optional[str] = None
    createdAt: str
    updatedAt: str
    ui: Optional[Preferences] = None
    modules: Optional[List[str]] = None


# =========================
#   SCHEMAS DE LOGIN
# =========================
class LoginRequest(BaseModel):
    login: str
    senha: constr(min_length=4)


class LoginResponse(BaseModel):
    accessToken: str
    accessTokenExpiresIn: int
    refreshToken: Optional[str] = None
    refreshTokenExpiresIn: Optional[int] = None
    user: User


# =========================
#   SCHEMAS DE REFRESH
# =========================
class RefreshResponse(BaseModel):
    accessToken: str
    accessTokenExpiresIn: int
    refreshToken: Optional[str] = None
    refreshTokenExpiresIn: Optional[int] = None


# =========================
#   SCHEMAS DE LOGOUT
# =========================
class LogoutResponse(BaseModel):
    ok: bool


# =========================
#   SCHEMAS DE RESET DE SENHA
# =========================
class RequestPasswordResetRequest(BaseModel):
    login: str


class RequestPasswordResetResponse(BaseModel):
    message: str = "Token de reset enviado por email/SMS"


class ConfirmPasswordResetRequest(BaseModel):
    token: str
    newPassword: constr(min_length=4)


class ConfirmPasswordResetResponse(BaseModel):
    message: str = "Senha alterada com sucesso"


# =========================
#   SCHEMAS DE ERRO
# =========================
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    traceId: Optional[str] = None


# =========================
#   SCHEMAS DE API KEY
# =========================
class ApiKeyValidationResponse(BaseModel):
    valid: bool


# =========================
#   HELPER FUNCTIONS
# =========================
def build_user_response(u) -> User:
    """Monta o objeto User (Pydantic) para resposta, sem campos sensíveis."""
    return User(
        id=u.id,
        login=u.login,
        nome=u.nome,
        email=u.email,
        whatsapp=u.whatsapp,
        isAdmin=u.isAdmin,
        status=u.status,
        lastLoginAt=u.lastLoginAt,
        lastLoginIp=u.lastLoginIp,
        createdAt=u.createdAt,
        updatedAt=u.updatedAt,
        ui=u.ui,
        modules=u.modules,
    )

