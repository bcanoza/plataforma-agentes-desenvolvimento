#!/usr/bin/env python3
"""
Seed de usuário admin inicial.
Uso (rodar na raiz do projeto, dentro do container):
  python -m app.db_schema.seed_admin --login admin --senha 1234 --email admin@example.com --nome "Admin"

Requer: psycopg2, passlib[bcrypt], settings (DB_*), e extensão citext já criada.
"""
from __future__ import annotations
import argparse
import uuid
from datetime import datetime, timezone

from passlib.hash import bcrypt
from app.controllers.db_controller import get_conn


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--login", required=True)
    p.add_argument("--senha", required=True)
    p.add_argument("--email", default=None)
    p.add_argument("--nome", default=None)
    args = p.parse_args(argv)

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verifica existência (CITEXT -> login case-insensitive)
            cur.execute("SELECT 1 FROM users WHERE login = LOWER(%s)", (args.login,))
            if cur.fetchone():
                print("Usuário já existe; nada a fazer.")
                return 0
            cur.execute(
                """
                INSERT INTO users (
                  id, login, nome, email, whatsapp, is_admin, status,
                  senha_hash, senha_updated_at, created_at, updated_at, ui, modules
                ) VALUES (
                  %s, LOWER(%s), %s, %s, NULL, TRUE, 'active',
                  %s, %s, %s, %s, '{"themePreferred":"vscode"}', ARRAY['home']
                )
                """,
                (
                    user_id,
                    args.login,
                    args.nome,
                    args.email,
                    bcrypt.hash(args.senha),
                    now,
                    now,
                    now,
                ),
            )
        conn.commit()
    print("Admin criado com sucesso:", args.login)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
