from __future__ import annotations
from pathlib import Path
from app.config import settings

from app.services.auth_service import AuthService, RS256TokenProvider, PasslibHasher, PasswordResetTokenRepo, PasswordResetTokenModel
from app.repositories.sql_repos import PgUserRepo, PgRefreshTokenRepo, PgAuditLogRepo


class MockPasswordResetTokenRepo(PasswordResetTokenRepo):
    """Repositório mock temporário para tokens de reset de senha."""
    
    def __init__(self):
        self._tokens = {}
    
    async def create(self, token: PasswordResetTokenModel) -> None:
        self._tokens[token.id] = token
    
    async def get_by_token(self, token: str) -> PasswordResetTokenModel | None:
        for t in self._tokens.values():
            if t.token == token:
                return t
        return None
    
    async def mark_as_used(self, token_id: str, when_iso: str) -> None:
        if token_id in self._tokens:
            self._tokens[token_id].usedAt = when_iso
    
    async def cleanup_expired(self, before_iso: str) -> int:
        # Implementação mock - não faz nada
        return 0


def _read_private_key() -> bytes:
    # SEM absolutizar; usa exatamente o path "app/..." como você pediu
    p = Path(settings.PRIVATE_KEY_PATH)          # ex.: "app/certs/jwt-private.pem"
    return p.read_bytes()                        # conteúdo PEM em bytes


def build_auth_service_from_settings() -> AuthService:
    iss = settings.JWT_ISS
    aud = [settings.JWT_AUD] if isinstance(settings.JWT_AUD, str) else list(settings.JWT_AUD)
    kid = settings.JWT_KID
    access_ttl = int(settings.ACCESS_TTL_SEC)
    refresh_ttl = int(settings.REFRESH_TTL_SEC)

    private_key_pem = _read_private_key()        # conteúdo do PEM em bytes

    token_provider = RS256TokenProvider(
        iss=iss,
        aud=aud,
        kid=kid,
        private_key_pem=private_key_pem,
        access_ttl_sec=access_ttl,
    )
    hasher = PasslibHasher("bcrypt")

    return AuthService(
        user_repo=PgUserRepo(),
        refresh_repo=PgRefreshTokenRepo(),
        password_reset_repo=MockPasswordResetTokenRepo(),
        audit_repo=PgAuditLogRepo(),
        hasher=hasher,
        token_provider=token_provider,
        refresh_ttl_sec=refresh_ttl,
    )
