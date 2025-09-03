# Módulos – Build Instruction (UI v7)

## Objetivo
Criar módulos plugáveis com manifesto `module.json`, botões e integrações de rede via Core.

## Passos
1) Criar pasta do módulo (ex.: `modules/chat/`).
2) Fornecer `module.json` validado por `docs/modules/module.schema.json`.
3) Declarar `buttons[]` (cada um com `id`, `label`, `route`, `icon`, `order`).
4) Declarar `apis[]` (id, baseUrl, auth) e `permissions[]` (ex.: `net:request`).
5) Usar `core.http.request/stream/upload` para chamadas HTTP.
6) Edição inline e padrões de UI devem seguir `docs/core/ui/ui.md`.
