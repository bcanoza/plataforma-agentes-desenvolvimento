# Endpoints – Auth

## POST /v1/auth/login
Body: `{ login, senha }` (senha ≥ 4).200: `{ accessToken, accessTokenExpiresIn, refreshToken?, refreshTokenExpiresIn?, user }`.Erros: `ERR_USER_NOT_FOUND`, `ERR_INVALID_SENHA`, `ERR_USER_DISABLED`.

## POST /v1/auth/refresh
Rotaciona o refresh. 200: novo `accessToken` (+ `refreshToken` quando transporte via body).

## POST /v1/auth/logout
Revoga refresh atual; idempotente: `{ ok: true }`.
