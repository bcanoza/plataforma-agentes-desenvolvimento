# ADRs (Architecture Decision Records)

## 001 – Tokens minimalistas
**Decisão**: Access JWT sem PII; preferências e módulos via `/users/me`.**Motivo**: Segurança, cacheabilidade, menor acoplamento.**Consequência**: Cliente sempre consulta `/users/me` pós-login.

## 002 – Core HTTP Bridge
**Decisão**: Módulos não usam `fetch`; chamam via ponte do Core.**Motivo**: Padronizar auth, erros, timeouts, telemetria e segurança.**Consequência**: Contrato único e previsível entre UI e servidor.

## 003 – Descoberta automática de módulos
**Decisão**: Core varre diretórios e registra módulos via `module.json`.**Motivo**: Simplicidade operacional, hot-plug de funcionalidades.**Consequência**: Manifesto é a fonte de verdade do módulo.
