#!/usr/bin/env bash
set -euo pipefail

API_BASE="https://api.odontoapi.com"   # <- fixo aqui
COOKIE_JAR="${COOKIE_JAR:-cookies.txt}"

usage() {
  cat <<EOF
usage: $(basename "$0") <comando> [args]

Comandos:
  login <login> <senha>     Faz login, salva cookie e exporta ACC (accessToken)
  refresh                   Usa o cookie para obter novo accessToken e exporta ACC
  me                        Chama /user/me usando ACC atual
  logout                    Faz logout (revoga refresh) e apaga cookie local

Variáveis de ambiente opcionais:
  COOKIE_JAR (default: ${COOKIE_JAR})

Exemplos:
  ./auth_cli.sh login admin 1234
  ./auth_cli.sh refresh
  ./auth_cli.sh me
  ./auth_cli.sh logout
EOF
}

ensure_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "Erro: jq não encontrado. Instale com: sudo apt-get install -y jq" >&2
    exit 1
  }
}

cmd_login() {
  local login="${1:-}"; local senha="${2:-}"
  if [[ -z "$login" || -z "$senha" ]]; then
    echo "Uso: $(basename "$0") login <login> <senha>" >&2
    exit 1
  fi

  ensure_jq

  local resp
  resp="$(curl -sS -X POST "${API_BASE}/auth/login" \
    -H "content-type: application/json" \
    --cookie-jar "${COOKIE_JAR}" \
    -d "{\"login\":\"${login}\",\"senha\":\"${senha}\"}")"

  ACC="$(echo "$resp" | jq -r '.accessToken // empty')"
  if [[ -z "${ACC:-}" || "${ACC}" == "null" ]]; then
    echo "Falha no login. Resposta:" >&2
    echo "$resp" | jq . >&2 || echo "$resp" >&2
    exit 1
  fi

  export ACC
  echo "Login OK. accessToken exportado na variável ACC"
  echo "ExpiresIn: $(echo "$resp" | jq -r '.accessTokenExpiresIn // "?"') s"
}

cmd_refresh() {
  ensure_jq

  local resp
  resp="$(curl -sS -X POST "${API_BASE}/auth/refresh" \
    --cookie-jar "${COOKIE_JAR}" --cookie "${COOKIE_JAR}")"

  ACC="$(echo "$resp" | jq -r '.accessToken // empty')"
  if [[ -z "${ACC:-}" || "${ACC}" == "null" ]]; then
    echo "Falha no refresh. Resposta:" >&2
    echo "$resp" | jq . >&2 || echo "$resp" >&2
    exit 1
  fi

  export ACC
  echo "Refresh OK. Novo accessToken exportado na variável ACC"
  echo "ExpiresIn: $(echo "$resp" | jq -r '.accessTokenExpiresIn // "?"') s"
}

cmd_me() {
  if [[ -z "${ACC:-}" ]]; then
    echo "ACC não definido. Rode: $(basename "$0") login <login> <senha> ou $(basename "$0") refresh" >&2
    exit 1
  fi

  curl -sS "${API_BASE}/user/me" \
    -H "Authorization: Bearer ${ACC}" | jq .
}

cmd_logout() {
  curl -sS -X POST "${API_BASE}/auth/logout" \
    --cookie-jar "${COOKIE_JAR}" --cookie "${COOKIE_JAR}" >/dev/null || true

  rm -f "${COOKIE_JAR}" || true
  unset ACC || true
  echo "Logout OK. Cookie local removido e ACC desfeito."
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    login)   shift; cmd_login "$@";;
    refresh) shift; cmd_refresh;;
    me)      shift; cmd_me;;
    logout)  shift; cmd_logout;;
    ""|-h|--help|help) usage;;
    *) echo "Comando desconhecido: $cmd" >&2; usage; exit 1;;
  esac
}

main "$@"
