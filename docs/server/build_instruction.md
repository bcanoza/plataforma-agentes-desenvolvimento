# Servidor – Build Instruction (UI v7)

## Objetivo
Implementar backend compatível com a UI v7 (tokens minimalistas; refresh opaco; preferências e módulos no perfil).

## Passos
1. Configurar ambiente (`config.md`, `examples/env.example`).
2. Modelar dados (`data_models/*.md`).
3. Implementar Auth (`endpoints/auth.md`, `contracts/auth.schema.json`): login, refresh (rotação), logout.
4. Implementar Users/Preferences: `/v1/users/me`, `/v1/users/me/preferences`.
5. Implementar Modules: `/v1/modules`, `/v1/users/me/modules`.
6. Implementar System: `/v1/health`, `/v1/version`, `/v1/time`.
7. Responder erros no shape `contracts/errors.schema.json`.
8. Segurança (`security.md`): CORS, CSRF (quando cookie), rate-limit, logs.
9. Observabilidade e QA (`ops/*.md`, `qa_checklist.md`).
