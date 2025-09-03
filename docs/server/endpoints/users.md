# Endpoints – Users

## GET /v1/users/me
Perfil do usuário autenticado (com preferências e módulos).

## PUT /v1/users/me/preferences
Atualiza `themePreferred`, `moduleOrder`, `iconOrder`.

## Admin
- GET /v1/users?search=&status=&isAdmin=
- POST /v1/users  (login único; senha ≥ 4)
- PUT /v1/users/:id
- POST /v1/users/:id/reset_senha
- POST /v1/users/:id/disable | /:id/enable
