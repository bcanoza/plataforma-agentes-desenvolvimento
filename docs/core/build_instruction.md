# Core – Build Instruction (UI v7)

## Objetivo
Construir o Core que governa sessão, temas, ActivityBar, descoberta de módulos, HTTP Bridge e eventos.

## Entradas
- `docs/core/core.config.schema.json` – configuração do Core.
- `docs/core/core.api.md` – contrato das APIs do Core (HTTP Bridge, eventos).
- `docs/core/login/*` – telas e fluxos de login/refresh/logout.
- `docs/core/main/*` – runtime pós-login (sincronização, montagem da ActivityBar).
- `docs/core/ui/ui.md` – padrões de UI (VS Code dark + WhatsApp light).

## Passos
1) **Config**: carregar config do Core e validar contra `core.config.schema.json`.
2) **Sessão**: implementar login/refresh/logout conforme `login.flows.md`.
3) **HTTP Bridge**: expor `core.http.request/stream/upload/abort` conforme `core.api.md`.
4) **Eventos**: publicar `net:*`, `auth:tokenRefreshed`, `logout` conforme `core.events.schema.json`.
5) **Temas**: aplicar tema inicial VS Code; permitir troca para WhatsApp light.
6) **Descoberta de módulos**: varrer diretórios, validar `module.json` com `modules/module.schema.json`.
7) **Sincronização**: após login, buscar `/users/me` e `/modules`, aplicar preferências e montar ActivityBar.
8) **Persistência leve**: manter preferências em memória e persistir alterações via `/users/me/preferences`.

## Saída
- Core funcional e estável para carregar módulos e operar a UI.
