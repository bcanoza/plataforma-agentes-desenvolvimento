# Core API (UI v7)

## HTTP Bridge
### `core.http.request(req)`
**Entrada**:
- `id?: string`
- `api: string` (id declarado no manifesto do módulo em `apis[]`)
- `path: string` (ex.: `/items`)
- `method: "GET"|"POST"|"PUT"|"PATCH"|"DELETE"`
- `query?: Record<string,string|number|boolean>`
- `headers?: Record<string,string>` (Core filtra proibidos e injeta `Authorization` quando `auth="core"`)
- `body?: any` (obj/string/FormData)
- `auth?: "core"|"none"|"custom"` (padrão: `"core"`)
- `timeoutMs?: number` (padrão global: 15000)
- `retries?: { max?: number, backoff?: "exponential"|"fixed", retryOn?: number[], methods?: string[], idempotencyKey?: string }`
- `stream?: "none"|"sse"|"ndjson"|"bytes"` (padrão: "none")
- `upload?: { kind: "multipart"|"binary", sizeLimitMb?: number }`

**Saída**:
- `{ status: number, ok: boolean, headers: Record<string,string>, data?|text?|blob?|stream?, error? }`
- `error` segue `docs/server/contracts/errors.schema.json` (+ `ERR_TIMEOUT|ERR_NETWORK|ERR_CORS`).

### `core.http.stream(req)`
- Igual ao `request` porém com `stream != "none"` e retorno de canal de eventos (`open`, `message`, `progress`, `error`, `close`).

### `core.http.upload(req)`
- Valida upload (tamanho, MIME); suporta chunking quando aplicável.

### `core.http.abort(id)`
- Cancela uma requisição/stream/transferência em andamento.

## Eventos (Core)
- `auth:tokenRefreshed`
- `net:request`, `net:response`, `net:error`
- `logout`

Ver schemas em `docs/core/core.events.schema.json` e descrição em `docs/core/events.md`.
