# Documentação – Build Instruction (UI v7)

## Objetivo
Roteiro **obrigatório** para criar/atualizar toda a documentação, contratos e schemas da UI.

## Estrutura mínima
```
docs/
├─ arch/              # overview.md, security.md, decisions.md
├─ core/              # build_instruction.md, core.api.md, *.schema.json, login/, main/, users/, ui/
├─ modules/           # build_instruction.md, module.schema.json, guide.md, policies.md, examples.md
├─ components/        # build_instruction.md
├─ server/            # build_instruction.md, contracts/, endpoints/, data_models/, ops/, examples/
├─ ops/               # qa-checklist.md, release.md
├─ site/              # index.html, index.md, navigation.md, theming.md
└─ documentation/     # (esta pasta)
```

## Passo a passo por área
1. **Arquitetura**: crie/atualize overview, segurança e ADRs.
2. **Core**: revise contratos (`core.api.md`, `core.config.schema.json`, `core.events.schema.json`), login (overview, flows, errors, schema), main (overview/runtime), users (schema + overview) e UI (padrões).
3. **Módulos**: valide `module.schema.json`, guide, policies e examples.
4. **Componentes**: mantenha build instruction de componentes reutilizáveis.
5. **Servidor**: atualize build instruction, contracts (OpenAPI + schemas), endpoints, data_models e ops.
6. **Ops**: QA e release atualizados.
7. **Site**: garanta `docs/site/index.html` navegável.

## Regras gerais
- **Sem placeholders** (“TODO” ou vazio) – todos os arquivos devem ter conteúdo real.
- **Schemas** sempre com `title`, `type`, `properties` e `required`.
- **OpenAPI** completo para todas as rotas em `/v1`.
- **UI Standards** idênticos aos definidos no Core.
- **Versione** a doc (ex.: v7, v7.1) quando houver mudanças relevantes.
