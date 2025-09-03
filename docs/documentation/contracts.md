# Documentação – Contracts (UI v7)

## Regra de ouro
**Nenhuma funcionalidade sem contrato**. Se existe endpoint ou entidade, existe contrato.

## Lista de contratos obrigatórios
- **Core**
  - `core.config.schema.json`
  - `core.events.schema.json`
  - `login/login.schema.json`
  - `users/user.schema.json`
- **Módulos**
  - `modules/module.schema.json`
- **Servidor (contracts/)**
  - `openapi.yaml`
  - `auth.schema.json`
  - `user.schema.json`
  - `preferences.schema.json`
  - `modules.schema.json`
  - `tokens.schema.json`
  - `errors.schema.json`

## Boas práticas
- JSON Schema Draft-07, sempre com `required` explícito.
- OpenAPI 3.0.3, paths versionados (`/v1`), exemplos de request/response.
- Nunca incluir PII em tokens; tokens minimalistas.
