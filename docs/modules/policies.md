# Políticas de Módulos

- **Sem fetch direto**: use sempre o Core HTTP Bridge.
- **Sem PII em querystring**.
- **IdempotencyKey** para POST reexecutáveis em caso de retry.
- **Limites**: respeitar concorrência por módulo; não travar a UI.
- **Streaming**: use `sse` ou `ndjson` via `core.http.stream` quando aplicável.
