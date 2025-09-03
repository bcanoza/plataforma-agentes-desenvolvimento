# Exemplos (descritivos)

## Lista paginada (page-based)
- Requisição: `GET /items?page=1&pageSize=20`
- Resposta: `{ items: [...], page: 1, pageSize: 20, total: 200 }`

## Lista paginada (cursor)
- Requisição: `GET /items?cursor=eyJ...`
- Resposta: `{ items: [...], nextCursor: "eyJ..." }`

## Upload (multipart)
- `upload.kind="multipart"`, tamanho validado pelo Core.

## Streaming (SSE/NDJSON)
- `stream="sse"` ou `stream="ndjson"`, eventos `message` com `data` já parseado.

## Erros & Toasts
- Respostas de erro seguem `errors.schema.json` + `ERR_TIMEOUT|ERR_NETWORK|ERR_CORS`.
