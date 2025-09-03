# Servidor – QA Checklist

- Login sucesso/erro; refresh rotação; logout idempotente.
- `/users/me` e `/users/me/preferences` OK.
- `/modules` e `/users/me/modules` OK.
- CORS/CSRF corretos; rate-limit; brute-force.
- Logs com traceId; health/version/time operantes.
