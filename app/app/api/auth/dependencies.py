# app/api/auth/dependencies.py
"""
Dependências de autenticação unificadas.
Combina API Key (microserviços) e JWT (UI) em um local.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional, List, TypedDict
from datetime import timezone, datetime

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError

from fastapi import Header, HTTPException, status, Depends
from app.config import settings


class CurrentUser(TypedDict):
    sub: str
    roles: List[str]
    sid: Optional[str]


@lru_cache(maxsize=1)
def _load_public_key_pem() -> str:
    """
    Lê e cacheia a chave pública usada para validar os JWTs RS256.
    Use settings.PUBLIC_KEY_PATH (PEM).
    """
    path = settings.PUBLIC_KEY_PATH
    with open(path, "rb") as f:
        pem = f.read()
    # PyJWT aceita bytes ou str
    return pem.decode() if isinstance(pem, (bytes, bytearray)) else pem


def _extract_bearer(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return parts[1].strip()


# =========================
#   API KEY (Microserviços)
# =========================
def verify_api_key(x_api_key: str = Header(..., convert_underscores=False)) -> bool:
    """
    Dependency para proteger endpoints com API Key.
    Lê a chave do cabeçalho `X-API-Key` e compara com settings.APP_SECRET.
    Usado para comunicação entre microserviços.
    """
    if x_api_key != settings.APP_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# =========================
#   JWT (UI)
# =========================
async def require_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """
    Dependency para proteger rotas com JWT.
    - Lê Authorization: Bearer <accessToken>
    - Valida com chave pública RS256
    - Checa iss/aud/exp
    - Retorna dict com sub/roles/sid
    """
    token = _extract_bearer(authorization)
    pubkey = _load_public_key_pem()

    try:
        claims = jwt.decode(
            token,
            pubkey,
            algorithms=["RS256"],
            audience=[settings.JWT_AUD] if isinstance(settings.JWT_AUD, str) else settings.JWT_AUD,
            issuer=settings.JWT_ISS,
            options={"require": ["exp", "iat", "sub"]},
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub")

    roles = claims.get("roles") or []
    sid = claims.get("sid")

    return {"sub": sub, "roles": roles, "sid": sid}


async def require_admin(current: CurrentUser = Depends(require_user)) -> CurrentUser:
    """
    Dependency que exige que o usuário tenha papel 'admin'.
    """
    roles = current.get("roles") or []
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current


# =========================
#   HÍBRIDO (API Key + JWT)
# =========================
async def require_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, convert_underscores=False)
) -> CurrentUser | bool:
    """
    Dependency híbrida que aceita tanto API Key quanto JWT.
    Útil para endpoints que podem ser chamados por microserviços ou UI.
    
    Retorna:
    - CurrentUser se autenticado via JWT
    - True se autenticado via API Key
    """
    # Prioridade: JWT primeiro, depois API Key
    if authorization:
        return await require_user(authorization)
    elif x_api_key:
        return verify_api_key(x_api_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing Authorization header or X-API-Key"
        )



