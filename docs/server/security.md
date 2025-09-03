# Servidor – Segurança

- CORS estrito; CSRF quando refresh via cookie.
- JWT RS256 com JWKS e `kid`; access curto (~15 min).
- Refresh opaco rotacionado; revogar no logout/refresh.
- Anti-bruteforce em login; rate-limit por IP/rota.
- Logs sem tokens; `traceId` nos erros.
