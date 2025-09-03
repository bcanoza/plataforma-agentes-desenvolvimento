# Core – Eventos

## `auth:tokenRefreshed`
- Emissão após refresh bem-sucedido.

## `net:request`
- Antes de enviar requisição via Core HTTP Bridge.

## `net:response`
- Na conclusão de uma requisição com status.

## `net:error`
- Em caso de falha; inclui `traceId` se disponível.

## `logout`
- Em logout explícito ou forçado.
