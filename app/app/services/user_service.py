# app/services/user_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from passlib.context import CryptContext

from app.repositories.sql_repos import PgUserRepo
from app.services.auth_service import UserModel  # reaproveita o domínio de usuário

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------
#   DTOs de entrada
# ---------------------------
@dataclass
class CreateUserInput:
    login: str
    email: Optional[str] = None
    nome: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: bool = False
    status: str = "active"           # "active" | "disabled"
    senha: Optional[str] = None      # se enviado, será hasheado
    modules: Optional[List[str]] = None
    ui: Optional[dict] = None


@dataclass
class UpdateUserInput:
    email: Optional[str] = None
    nome: Optional[str] = None
    whatsapp: Optional[str] = None
    isAdmin: Optional[bool] = None
    status: Optional[str] = None
    modules: Optional[List[str]] = None
    ui: Optional[dict] = None


# ---------------------------
#       Serviço
# ---------------------------
class UserService:
    """
    Camada de negócio para Usuários.
    Observação: este service delega ao PgUserRepo as operações de persistência.
    Os métodos abaixo assumem que o repositório expõe:
      - find_by_id(user_id) -> Optional[UserModel]
      - find_by_login(login) -> Optional[UserModel]
      - search(q, limit, offset) -> Tuple[List[UserModel], int]
      - insert_user(...campos...) -> UserModel
      - update_user(user_id, ...campos...) -> Optional[UserModel]
      - delete_user(user_id) -> bool
      - set_password(user_id, senha_hash, when_iso) -> bool
    """
    def __init__(self, repo: Optional[PgUserRepo] = None) -> None:
        self.repo = repo or PgUserRepo()

    # ---------- READ ----------
    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """Usado, por exemplo, no endpoint /user/me (via sub do JWT)."""
        return await self.repo.find_by_id(user_id)

    async def get_by_login(self, login: str) -> Optional[UserModel]:
        return await self.repo.find_by_login(login)

    async def list_users(self, *, q: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[List[UserModel], int]:
        """
        Retorna (items, total). Busca por login/nome/email quando `q` informado.
        """
        return await self.repo.search(q=q, limit=limit, offset=offset)

    # ---------- CREATE ----------
    async def create_user(self, inp: CreateUserInput) -> UserModel:
        # valida login único
        existing = await self.repo.find_by_login(inp.login)
        if existing:
            raise ValueError("LOGIN_ALREADY_EXISTS")

        now = datetime.now(timezone.utc).isoformat()
        senha_hash = pwd_ctx.hash(inp.senha) if inp.senha else None

        user = await self.repo.insert_user(
            login=inp.login,
            email=inp.email,
            nome=inp.nome,
            whatsapp=inp.whatsapp,
            is_admin=inp.isAdmin,
            status=inp.status,
            senha_hash=senha_hash,
            senha_updated_at=now if senha_hash else None,
            created_at=now,
            updated_at=now,
            modules=inp.modules,
            ui=inp.ui,
        )
        return user

    # ---------- UPDATE ----------
    async def update_user(self, user_id: str, inp: UpdateUserInput) -> Optional[UserModel]:
        now = datetime.now(timezone.utc).isoformat()
        updated = await self.repo.update_user(
            user_id=user_id,
            email=inp.email,
            nome=inp.nome,
            whatsapp=inp.whatsapp,
            is_admin=inp.isAdmin,
            status=inp.status,
            modules=inp.modules,
            ui=inp.ui,
            updated_at=now,
        )
        return updated

    # ---------- DELETE ----------
    async def delete_user(self, user_id: str) -> bool:
        """
        Remoção física. Se preferir soft delete, troque para update_user(status='disabled').
        """
        return await self.repo.delete_user(user_id)

    # ---------- PASSWORD ----------
    async def change_password(self, user_id: str, nova_senha: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        senha_hash = pwd_ctx.hash(nova_senha)
        return await self.repo.set_password(user_id=user_id, senha_hash=senha_hash, when_iso=now)
