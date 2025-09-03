# Main – Runtime

## Sincronização de Preferências
1. Após login: `GET /v1/users/me` → `themePreferred`, `moduleOrder`, `iconOrder`, `modules` opcionais.
2. `GET /v1/modules` → manifestos disponíveis com `order` e `buttons[].order`.
3. Monta ActivityBar seguindo:
   - Ordem do usuário (`moduleOrder`) quando existir;
   - Itens não listados entram por `order desc`, `id asc`;
   - Ícones seguem `iconOrder` + `buttons[].order`.

## Aplicação de Tema
- Aplica `themePreferred`, exceto quando modo fixo do Core estiver ativo.

## Eventos
- Emite `net:*` ao usar HTTP Bridge e `auth:tokenRefreshed` quando renovar token.
