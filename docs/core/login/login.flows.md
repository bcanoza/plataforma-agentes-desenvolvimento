# Login – Fluxos

## 1) Login
1. Core envia `{ login, senha }` para `/v1/auth/login`.
2. Recebe `accessToken` (JWT), `refreshToken` (opaco via cookie/body) e `user`.
3. Salva estado da sessão e chama `/v1/users/me` para perfil atualizado.

## 2) Refresh (rotação)
- Antes do `accessToken` expirar, Core chama `/v1/auth/refresh` e **revoga** o refresh anterior.

## 3) Logout
- Core chama `/v1/auth/logout` e limpa sessão local.
