#!/usr/bin/env python3
"""
Script para criar as tabelas de autenticação no Postgres.
-------------------------------------------------------
Usa o get_conn() do db_controller para abrir a conexão.

Tabelas criadas:
  - users
  - refresh_tokens
  - audit_log
  - sessions (opcional, com --with-sessions)

Como usar:
  python db_script/create_auth_schema.py --with-sessions
"""

import argparse
from app.controllers.db_controller import get_conn

USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id               TEXT PRIMARY KEY,
  login            CITEXT UNIQUE NOT NULL,
  nome             TEXT,
  email            TEXT,
  whatsapp         TEXT,
  is_admin         BOOLEAN NOT NULL DEFAULT FALSE,
  status           TEXT NOT NULL CHECK (status IN ('active','disabled')),
  senha_hash       TEXT NOT NULL,
  senha_updated_at TIMESTAMPTZ,
  last_login_at    TIMESTAMPTZ,
  last_login_ip    INET,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ui               JSONB,
  modules          TEXT[]
);
"""

REFRESH_TOKENS_SQL = """
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id          TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sid         TEXT NOT NULL,
  issued_at   TIMESTAMPTZ NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked_at  TIMESTAMPTZ,
  user_agent  TEXT,
  client_ip   INET
);
"""

AUDIT_LOG_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
  id         BIGSERIAL PRIMARY KEY,
  user_id    TEXT REFERENCES users(id) ON DELETE SET NULL,
  event      TEXT NOT NULL,
  metadata   JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
  sid           TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at  TIMESTAMPTZ,
  terminated_at TIMESTAMPTZ
);
"""

INDEXES_SQL = """
-- users
CREATE EXTENSION IF NOT EXISTS citext;
CREATE INDEX IF NOT EXISTS idx_users_status        ON users(status);

-- refresh_tokens
CREATE INDEX IF NOT EXISTS idx_rt_user_id          ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_rt_sid              ON refresh_tokens(sid);
CREATE INDEX IF NOT EXISTS idx_rt_expires_at       ON refresh_tokens(expires_at);

-- audit_log
CREATE INDEX IF NOT EXISTS idx_audit_user_id       ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at    ON audit_log(created_at);
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-sessions", action="store_true", help="Cria a tabela sessions também")
    args = parser.parse_args()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS citext;")
            cur.execute(USERS_SQL)
            cur.execute(REFRESH_TOKENS_SQL)
            cur.execute(AUDIT_LOG_SQL)
            if args.with_sessions:
                cur.execute(SESSIONS_SQL)
            # índices
            for stmt in INDEXES_SQL.strip().split(";\n"):
                if stmt.strip():
                    cur.execute(stmt)
        conn.commit()
        print("Esquema de autenticação criado/atualizado com sucesso.")


if __name__ == "__main__":
    main()
