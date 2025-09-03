# app/services/auth_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Protocol, Dict, Any
import uuid

import jwt  # PyJWT
from passlib.context import CryptContext

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend




# =========================
#   Modelos de Domínio
# =========================
@dataclass
class UserModel:
    id: str
    login: str
    nome: Optional[str]
    email: Optional[str]
    whatsapp: Optional[str]
    isAdmin: bool
    status: str  # "active" | "disabled"
    senhaHash: str
    senhaUpdatedAt: Optional[str]
    lastLoginAt: Optional[str]
    lastLoginIp: Optional[str]
    createdAt: str
    updatedAt: str
    ui: Optional[dict]
    modules: Optional[List[str]]


@dataclass
class RefreshTokenModel:
    id: str
    userId: str
    sid: str
    issuedAt: str
    expiresAt: str
    revokedAt: Optional[str]
    userAgent: Optional[str]
    clientIp: Optional[str]


@dataclass
class PasswordResetTokenModel:
    id: str
    userId: str
    token: str  # token opaco para o usuário
    issuedAt: str
    expiresAt: str
    usedAt: Optional[str]
    userAgent: Optional[str]
    clientIp: Optional[str]


@dataclass
class TokenBundle:
    access_token: str
    access_expires_in: int
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    user: Optional[UserModel] = None


# =========================
#        Portas
# =========================
class UserRepo(Protocol):
    async def find_by_login(self, login: str) -> Optional[UserModel]: ...
    async def find_by_id(self, user_id: str) -> Optional[UserModel]: ...
    async def update_last_login(self, user_id: str, when_iso: str, ip: Optional[str]) -> None: ...


class RefreshTokenRepo(Protocol):
    async def create(self, token: RefreshTokenModel) -> None: ...
    async def get(self, token_id: str) -> Optional[RefreshTokenModel]: ...
    async def revoke(self, token_id: str, when_iso: str) -> None: ...
    async def revoke_by_sid(self, sid: str, when_iso: str) -> None: ...
    async def revoke_by_user_id(self, user_id: str, when_iso: str) -> None: ...
    async def cleanup_expired(self, before_iso: str) -> int: ...


class PasswordResetTokenRepo(Protocol):
    async def create(self, token: PasswordResetTokenModel) -> None: ...
    async def get_by_token(self, token: str) -> Optional[PasswordResetTokenModel]: ...
    async def mark_as_used(self, token_id: str, when_iso: str) -> None: ...
    async def cleanup_expired(self, before_iso: str) -> int: ...


class AuditLogRepo(Protocol):
    async def write(self, user_id: Optional[str], event: str, metadata: Dict[str, Any]) -> None: ...


class PasswordHasher(Protocol):
    def verify(self, plain_password: str, password_hash: str) -> bool: ...


class TokenProvider(Protocol):
    def mint_access(
        self, *, sub: str, sid: str, roles: List[str], ver: int = 1,
        amr: Optional[List[str]] = None, auth_time: Optional[int] = None
    ) -> tuple[str, int]: ...


# =========================
#   Implementações util
# =========================
class PasslibHasher:
    def __init__(self, scheme: str = "bcrypt") -> None:
        self._ctx = CryptContext(schemes=[scheme], deprecated="auto")

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._ctx.verify(plain_password, password_hash)
        except Exception:
            return False

    def hash(self, plain_password: str) -> str:
        return self._ctx.hash(plain_password)

class RS256TokenProvider:
    """
    Provedor simples de JWT RS256. Carrega a chave privada via `cryptography`
    para suportar PKCS#1 (RSA PRIVATE KEY) e PKCS#8 (PRIVATE KEY) de forma robusta.
    """
    def __init__(self, *, iss: str, aud: List[str], kid: str, private_key_pem: str, access_ttl_sec: int) -> None:
        self.iss = iss
        self.aud = aud
        self.kid = kid
        self.access_ttl_sec = access_ttl_sec

        # Normaliza e carrega a chave privada com cryptography
        key_bytes = private_key_pem.encode() if isinstance(private_key_pem, str) else private_key_pem
        self._private_key = serialization.load_pem_private_key(
            key_bytes,
            password=None,
            backend=default_backend(),
        )

    def mint_access(
        self, *, sub: str, sid: str, roles: List[str], ver: int = 1,
        amr: Optional[List[str]] = None, auth_time: Optional[int] = None
    ) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        exp = int((now + timedelta(seconds=self.access_ttl_sec)).timestamp())
        jti = str(uuid.uuid4())
        claims: Dict[str, Any] = {
            "iss": self.iss,
            "aud": self.aud,
            "sub": sub,
            "iat": iat,
            "exp": exp,
            "jti": jti,
            "sid": sid,
            "ver": ver,
            "roles": roles,
        }
        if amr:
            claims["amr"] = amr
        if auth_time is not None:
            claims["auth_time"] = auth_time

        headers = {"kid": self.kid, "alg": "RS256", "typ": "JWT"}
        # Passa o OBJETO da chave privada (já carregado) para o PyJWT
        token = jwt.encode(claims, self._private_key, algorithm="RS256", headers=headers)
        return token, self.access_ttl_sec


# =========================
#       Exceções
# =========================
class AuthError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# =========================
#        Serviço
# =========================
class AuthService:
    def __init__(
        self,
        user_repo: UserRepo,
        refresh_repo: RefreshTokenRepo,
        password_reset_repo: PasswordResetTokenRepo,
        audit_repo: AuditLogRepo,
        hasher: PasswordHasher,
        token_provider: TokenProvider,
        refresh_ttl_sec: int,
        password_reset_ttl_sec: int = 900,  # 15 minutos
    ) -> None:
        self.users = user_repo
        self.refresh = refresh_repo
        self.password_reset = password_reset_repo
        self.audit = audit_repo
        self.hasher = hasher
        self.token_provider = token_provider
        self.refresh_ttl_sec = refresh_ttl_sec
        self.password_reset_ttl_sec = password_reset_ttl_sec

    # ------------- PUBLIC API -------------
    async def login(self, *, login: str, senha: str, user_agent: Optional[str], client_ip: Optional[str]) -> TokenBundle:
        user = await self.users.find_by_login(login)
        if not user:
            await self.audit.write(None, "login_fail", {"login": login, "reason": "not_found"})
            raise AuthError("ERR_USER_NOT_FOUND", "Usuário não encontrado")

        if user.status != "active":
            await self.audit.write(user.id, "login_fail", {"login": login, "reason": "disabled"})
            raise AuthError("ERR_USER_DISABLED", "Usuário desativado")

        if not self.hasher.verify(senha, user.senhaHash):
            await self.audit.write(user.id, "login_fail", {"login": login, "reason": "invalid_password"})
            raise AuthError("ERR_INVALID_SENHA", "Senha inválida")

        # criar sessão (sid) e refresh token
        sid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        issued_at = now.isoformat()
        expires_at = (now + timedelta(seconds=self.refresh_ttl_sec)).isoformat()

        refresh = RefreshTokenModel(
            id=str(uuid.uuid4()),
            userId=user.id,
            sid=sid,
            issuedAt=issued_at,
            expiresAt=expires_at,
            revokedAt=None,
            userAgent=user_agent,
            clientIp=client_ip,
        )
        await self.refresh.create(refresh)

        # access token
        roles = ["admin"] if user.isAdmin else ["user"]
        access, access_ttl = self.token_provider.mint_access(sub=user.id, sid=sid, roles=roles, ver=1)

        await self.users.update_last_login(user.id, issued_at, client_ip)
        await self.audit.write(user.id, "login_success", {"sid": sid, "rt": refresh.id})

        return TokenBundle(
            access_token=access,
            access_expires_in=access_ttl,
            refresh_token=refresh.id,
            refresh_expires_in=self.refresh_ttl_sec,
            user=user,
        )

    async def refresh_token(
        self, *, raw_refresh_token: Optional[str], user_agent: Optional[str], client_ip: Optional[str]
    ) -> TokenBundle:
        if not raw_refresh_token:
            raise AuthError("ERR_REFRESH_MISSING", "Refresh token ausente")

        token = await self.refresh.get(raw_refresh_token)
        if not token:
            raise AuthError("ERR_REFRESH_INVALID", "Refresh token inválido")

        now = datetime.now(timezone.utc)
        if token.revokedAt is not None:
            raise AuthError("ERR_REFRESH_REVOKED", "Refresh token revogado")
        if datetime.fromisoformat(token.expiresAt) <= now:
            raise AuthError("ERR_REFRESH_EXPIRED", "Refresh token expirado")

        # carregar usuário por ID
        user = await self.users.find_by_id(token.userId)
        if user is None:
            raise AuthError("ERR_USER_NOT_FOUND", "Usuário não encontrado")
        if user.status != "active":
            raise AuthError("ERR_USER_DISABLED", "Usuário desativado")

        # rotação de refresh
        await self.refresh.revoke(token.id, now.isoformat())
        new_token = RefreshTokenModel(
            id=str(uuid.uuid4()),
            userId=user.id,
            sid=token.sid,
            issuedAt=now.isoformat(),
            expiresAt=(now + timedelta(seconds=self.refresh_ttl_sec)).isoformat(),
            revokedAt=None,
            userAgent=user_agent,
            clientIp=client_ip,
        )
        await self.refresh.create(new_token)

        # novo access
        roles = ["admin"] if user.isAdmin else ["user"]
        access, access_ttl = self.token_provider.mint_access(sub=user.id, sid=token.sid, roles=roles, ver=1)
        await self.audit.write(user.id, "refresh", {"old": token.id, "new": new_token.id})

        return TokenBundle(
            access_token=access,
            access_expires_in=access_ttl,
            refresh_token=new_token.id,
            refresh_expires_in=self.refresh_ttl_sec,
            user=None,
        )

    async def logout(self, *, raw_refresh_token: Optional[str]) -> None:
        if not raw_refresh_token:
            return  # idempotente
        token = await self.refresh.get(raw_refresh_token)
        if not token:
            return  # idempotente
        if token.revokedAt is not None:
            return  # idempotente
        now = datetime.now(timezone.utc).isoformat()
        await self.refresh.revoke(token.id, now)
        await self.audit.write(token.userId, "logout", {"rt": token.id})

    # ------------- PASSWORD RESET API -------------
    async def request_password_reset(self, *, login: str, user_agent: Optional[str], client_ip: Optional[str]) -> str:
        """
        Solicita reset de senha. Retorna token para o usuário (que será enviado por email/SMS).
        """
        user = await self.users.find_by_login(login)
        if not user:
            # Por segurança, não revelamos se o usuário existe
            await self.audit.write(None, "password_reset_request", {"login": login, "reason": "not_found"})
            raise AuthError("ERR_USER_NOT_FOUND", "Usuário não encontrado")

        if user.status != "active":
            await self.audit.write(user.id, "password_reset_request", {"login": login, "reason": "disabled"})
            raise AuthError("ERR_USER_DISABLED", "Usuário desativado")

        # Gerar token de reset
        reset_token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        issued_at = now.isoformat()
        expires_at = (now + timedelta(seconds=self.password_reset_ttl_sec)).isoformat()

        reset_model = PasswordResetTokenModel(
            id=str(uuid.uuid4()),
            userId=user.id,
            token=reset_token,
            issuedAt=issued_at,
            expiresAt=expires_at,
            usedAt=None,
            userAgent=user_agent,
            clientIp=client_ip,
        )
        await self.password_reset.create(reset_model)
        await self.audit.write(user.id, "password_reset_request", {"token_id": reset_model.id})

        return reset_token

    async def confirm_password_reset(self, *, reset_token: str, new_password: str, user_agent: Optional[str], client_ip: Optional[str]) -> None:
        """
        Confirma reset de senha com token válido.
        """
        if not reset_token:
            raise AuthError("ERR_RESET_TOKEN_MISSING", "Token de reset ausente")

        token_model = await self.password_reset.get_by_token(reset_token)
        if not token_model:
            raise AuthError("ERR_RESET_TOKEN_INVALID", "Token de reset inválido")

        now = datetime.now(timezone.utc)
        if token_model.usedAt is not None:
            raise AuthError("ERR_RESET_TOKEN_USED", "Token de reset já foi utilizado")
        if datetime.fromisoformat(token_model.expiresAt) <= now:
            raise AuthError("ERR_RESET_TOKEN_EXPIRED", "Token de reset expirado")

        # Carregar usuário
        user = await self.users.find_by_id(token_model.userId)
        if not user:
            raise AuthError("ERR_USER_NOT_FOUND", "Usuário não encontrado")
        if user.status != "active":
            raise AuthError("ERR_USER_DISABLED", "Usuário desativado")

        # Atualizar senha
        new_hash = self.hasher.hash(new_password)
        now_iso = now.isoformat()
        await self.users.update_password(user.id, new_hash, now_iso)

        # Marcar token como usado
        await self.password_reset.mark_as_used(token_model.id, now_iso)

        # Invalidar todas as sessões do usuário
        await self.refresh.revoke_by_user_id(token_model.userId, now_iso)

        await self.audit.write(user.id, "password_reset_success", {"token_id": token_model.id})

    async def change_own_password(self, *, user_id: str, current_password: str, new_password: str, user_agent: Optional[str], client_ip: Optional[str]) -> None:
        """
        Usuário troca sua própria senha (precisa saber a senha atual).
        """
        user = await self.users.find_by_id(user_id)
        if not user:
            raise AuthError("ERR_USER_NOT_FOUND", "Usuário não encontrado")
        if user.status != "active":
            raise AuthError("ERR_USER_DISABLED", "Usuário desativado")

        # Verificar senha atual
        if not self.hasher.verify(current_password, user.senhaHash):
            await self.audit.write(user.id, "password_change_fail", {"reason": "invalid_current_password"})
            raise AuthError("ERR_INVALID_CURRENT_PASSWORD", "Senha atual incorreta")

        # Atualizar senha
        new_hash = self.hasher.hash(new_password)
        now_iso = datetime.now(timezone.utc).isoformat()
        await self.users.update_password(user.id, new_hash, now_iso)

        # Invalidar todas as sessões do usuário (exceto a atual)
        await self.refresh.revoke_by_user_id(user.id, now_iso)

        await self.audit.write(user.id, "password_change_success", {})



