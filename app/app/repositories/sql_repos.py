# app/repositories/sql_repos.py
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime
from psycopg2.extras import Json

from app.controllers.db_controller import get_conn
from app.services.auth_service import (
    UserModel, RefreshTokenModel,
    UserRepo, RefreshTokenRepo, AuditLogRepo
)


class PgUserRepo(UserRepo):
    async def find_by_login(self, login: str) -> Optional[UserModel]:
        sql = """
        SELECT id, login, nome, email, whatsapp, is_admin, status, senha_hash,
               senha_updated_at, last_login_at, last_login_ip,
               created_at, updated_at, ui, modules
        FROM users
        WHERE login = LOWER(%s)
        LIMIT 1
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (login,))
            row = cur.fetchone()
        return _to_user(row) if row else None

    async def find_by_id(self, user_id: str) -> Optional[UserModel]:
        sql = """
        SELECT id, login, nome, email, whatsapp, is_admin, status, senha_hash,
               senha_updated_at, last_login_at, last_login_ip,
               created_at, updated_at, ui, modules
        FROM users
        WHERE id = %s
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
        return _to_user(row) if row else None

    async def update_last_login(self, user_id: str, when_iso: str, ip: Optional[str]) -> None:
        sql = "UPDATE users SET last_login_at=%s, last_login_ip=%s, updated_at=NOW() WHERE id=%s"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (when_iso, ip, user_id))
            conn.commit()

    async def update_password(self, user_id: str, new_hash: str, when_iso: str) -> None:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                       SET senha_hash = %s,
                           senha_updated_at = %s,
                           updated_at = %s
                     WHERE id = %s
                    """,
                    (new_hash, when_iso, when_iso, user_id),
                )


class PgRefreshTokenRepo(RefreshTokenRepo):
    async def create(self, token: RefreshTokenModel) -> None:
        sql = """
        INSERT INTO refresh_tokens (id, user_id, sid, issued_at, expires_at,
                                    revoked_at, user_agent, client_ip)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                token.id, token.userId, token.sid, token.issuedAt,
                token.expiresAt, token.revokedAt, token.userAgent, token.clientIp
            ))
            conn.commit()

    async def get(self, token_id: str) -> Optional[RefreshTokenModel]:
        sql = """
        SELECT id, user_id, sid, issued_at, expires_at,
               revoked_at, user_agent, client_ip
        FROM refresh_tokens WHERE id=%s
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (token_id,))
            row = cur.fetchone()
        return _to_refresh(row) if row else None

    async def revoke(self, token_id: str, when_iso: str) -> None:
        sql = "UPDATE refresh_tokens SET revoked_at=%s WHERE id=%s AND revoked_at IS NULL"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (when_iso, token_id))
            conn.commit()

    async def revoke_by_sid(self, sid: str, when_iso: str) -> None:
        sql = "UPDATE refresh_tokens SET revoked_at=%s WHERE sid=%s AND revoked_at IS NULL"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (when_iso, sid))
            conn.commit()

    async def cleanup_expired(self, before_iso: str) -> int:
        sql = "DELETE FROM refresh_tokens WHERE expires_at < %s"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (before_iso,))
            deleted = cur.rowcount
            conn.commit()
        return int(deleted)


class PgAuditLogRepo(AuditLogRepo):
    async def write(self, user_id: Optional[str], event: str, metadata: Dict[str, Any]) -> None:
        sql = "INSERT INTO audit_log (user_id, event, metadata) VALUES (%s,%s,%s)"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, event, Json(metadata)))
            conn.commit()

# -----------------------------------------------------------------------------
# utils
# -----------------------------------------------------------------------------
def _to_user(row) -> UserModel:
    return UserModel(
        id=row[0],
        login=row[1],
        nome=row[2],
        email=row[3],
        whatsapp=row[4],
        isAdmin=row[5],
        status=row[6],
        senhaHash=row[7],
        senhaUpdatedAt=_iso(row[8]),
        lastLoginAt=_iso(row[9]),
        lastLoginIp=str(row[10]) if row[10] else None,
        createdAt=_iso(row[11]),
        updatedAt=_iso(row[12]),
        ui=row[13],
        modules=row[14],
    )


def _to_refresh(row) -> RefreshTokenModel:
    return RefreshTokenModel(
        id=row[0],
        userId=row[1],
        sid=row[2],
        issuedAt=_iso(row[3]),
        expiresAt=_iso(row[4]),
        revokedAt=_iso(row[5]),
        userAgent=row[6],
        clientIp=str(row[7]) if row[7] else None,
    )


def _iso(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
