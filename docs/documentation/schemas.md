# Documentação – Schemas (UI v7)

## JSON Schema (padrão)
- Use `$schema: http://json-schema.org/draft-07/schema#`.
- Inclua `title`, `type`, `properties`, `required`.
- Use `enum` para valores fechados; `format` (ex.: `uri`, `email`) quando aplicável.

### Exemplo mínimo
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "UserPublic",
  "type": "object",
  "required": ["id","login","isAdmin","status"],
  "properties": {
    "id": { "type": "string" },
    "login": { "type": "string" },
    "isAdmin": { "type": "boolean" },
    "status": { "type": "string", "enum": ["active","disabled"] }
  }
}
```

## OpenAPI (padrão)
- Versão `openapi: 3.0.3`.
- Descrever cada rota com request/response e exemplos.
- Reutilizar schemas em `components/schemas`.
