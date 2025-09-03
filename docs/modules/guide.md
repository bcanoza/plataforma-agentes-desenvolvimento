# Guia de Módulos

## Manifesto
- `id`, `name`, `kind`, `version`, `order`, `buttons[]`, `apis[]`, `permissions[]`.

## Botões
- Cada botão define `route` interna e `icon` (Codicon recomendado).

## HTTP via Core
- Chame `core.http.request/stream/upload`.
- `auth="core"` injeta `Authorization` automaticamente.

## Boas práticas de UI
- Edição inline; toasts para confirmações.
- ActivityBar segue `order` do módulo (maior primeiro) + override do usuário.
