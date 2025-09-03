# app/api/users/routes.py
"""
Controller de usuários - CRUD, perfil, preferências.
"""
from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.services.user_service import UserService, CreateUserInput, UpdateUserInput
from app.api.auth.dependencies import require_user, require_admin, CurrentUser
from app.api.auth.schemas import User, build_user_response
from .schemas import CreateUserRequest, UpdateUserRequest, ChangeOwnPasswordRequest

router = APIRouter(prefix="/v1/users", tags=["Users"])
service = UserService()


# =========================
#   ENDPOINTS PÚBLICOS
# =========================
@router.get("/me", response_model=User)
async def me(current: CurrentUser = Depends(require_user)):
    """Perfil do usuário autenticado."""
    u = await service.get_user_by_id(current["sub"])
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return build_user_response(u)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    body: ChangeOwnPasswordRequest, 
    current: CurrentUser = Depends(require_user),
    req: Request = None
):
    """Usuário troca sua própria senha (precisa saber a senha atual)."""
    from app.services.auth_wiring import build_auth_service_from_settings
    from app.api.auth.routes import _client_hints
    
    auth_service = build_auth_service_from_settings()
    ua, ip = _client_hints(req) if req else (None, None)
    
    await auth_service.change_own_password(
        user_id=current["sub"],
        current_password=body.currentPassword,
        new_password=body.newPassword,
        user_agent=ua,
        client_ip=ip,
    )
    return None


# =========================
#   ENDPOINTS ADMIN
# =========================
@router.get("/", response_model=List[User])
async def list_users(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _: CurrentUser = Depends(require_admin),
):
    """Lista usuários (admin)."""
    users, total = await service.list_users(q=q, limit=limit, offset=offset)
    return [build_user_response(u) for u in users]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, _: CurrentUser = Depends(require_admin)):
    """Busca usuário por ID (admin)."""
    u = await service.get_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return build_user_response(u)


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest, _: CurrentUser = Depends(require_admin)):
    """Cria novo usuário (admin)."""
    try:
        u = await service.create_user(CreateUserInput(**body.dict()))
        return build_user_response(u)
    except ValueError as e:
        if str(e) == "LOGIN_ALREADY_EXISTS":
            raise HTTPException(status_code=400, detail="Login já existe")
        raise


@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, body: UpdateUserRequest, _: CurrentUser = Depends(require_admin)):
    """Atualiza usuário (admin)."""
    u = await service.update_user(user_id, UpdateUserInput(**body.dict()))
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return build_user_response(u)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, _: CurrentUser = Depends(require_admin)):
    """Remove usuário (admin)."""
    ok = await service.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return None


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(user_id: str, _: CurrentUser = Depends(require_admin)):
    """Admin força reset de senha (usuário precisará usar o fluxo de reset)."""
    # TODO: Implementar lógica para admin forçar reset
    # Por enquanto, apenas retorna sucesso
    return None



