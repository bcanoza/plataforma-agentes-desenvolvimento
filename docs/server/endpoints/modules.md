# Endpoints – Modules

## GET /v1/modules
Lista manifestos disponíveis (id, name, kind, version, order, buttons[].order).

## GET /v1/users/me/modules
Retorna opcionais habilitados: `{ modules: string[] }`.

## PUT /v1/users/me/modules
Atualiza opcionais habilitados: `{ modules: string[] }`.
