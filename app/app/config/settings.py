"""Configurações globais da aplicação."""
from __future__ import annotations

import os

# --------------------------------------------------------------------
# Diretórios-base e estrutura de projeto
# --------------------------------------------------------------------

# Diretório atual do processo dentro do container (normalmente "/app/app")
BASE_DIR = os.getcwd()

# Caminho lógico do projeto a partir da raiz do container; mantemos a compat:
# Ex.: "app/app" (não use barra inicial aqui)
APP_ROOT = os.getenv("APP_ROOT", "app/app").strip().strip("/")

# Nome do ponto de montagem (ex.: "/app" -> "app"); ajuda a evitar "app/app/app"
_MOUNT_NAME = os.path.basename(BASE_DIR.rstrip("/")) or "app"

# Remove prefixo redundante "app/" quando existir (ex.: "app/app" -> "app")
if APP_ROOT.startswith(f"{_MOUNT_NAME}/"):
    RELATIVE_APP_PATH = APP_ROOT[len(_MOUNT_NAME) + 1 :]
else:
    RELATIVE_APP_PATH = APP_ROOT

# Caminho absoluto da raiz do projeto (ex.: "/app/app")
PROJECT_ROOT_ABS = (
    APP_ROOT if os.path.isabs(APP_ROOT)
    else os.path.normpath(os.path.join(BASE_DIR, RELATIVE_APP_PATH))
)

# Diretório padrão de testes relativo ao BASE_DIR (fica "/app/tests" quando usado fora)
DEFAULT_TESTS_DIR = os.getenv("TESTS_DIR", "tests").strip().strip("/")

# Diretório dos contratos YAML da camada de IA (tools/dispatcher/orchestrator)
# Ex.: "/app/app/docs/contracts"
CONTRACTS_DIR = os.getenv(
    "CONTRACTS_DIR",
    os.path.join(PROJECT_ROOT_ABS, "docs", "contracts"),
)


PATCH_CWD = ""

# --------------------------------------------------------------------
# App / Logs / Ambiente
# --------------------------------------------------------------------

# Nome padrão do logger
LOGGER_NAME = os.getenv("LOGGER_NAME", "assistente")

# Variáveis de ambiente comuns
APP_ENV = os.getenv("APP_ENV", "dev")
APP_SECRET = os.getenv("APP_SECRET", "default_secret")
TZ = os.getenv("TZ", "America/Sao_Paulo")

# Arquivo de log:
# - use um caminho RELATIVO (padrão "logs/app.log"), para escrever sob /app/app/logs
# - se quiser absoluto, passe LOG_FILE iniciando com "/"
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log").strip()

# Diretórios lógicos (mantidos por compatibilidade — usados em alguns pontos)
CONTROLLERS_PACKAGE = "app.controllers"
DOCS_DIR = os.path.join(APP_ROOT, "docs")
MODELS_DIR = os.path.join(APP_ROOT, "models")
TESTS_DIR = os.path.join(APP_ROOT, "tests")

# --------------------------------------------------------------------
# Banco de dados / Redis / Celery
# --------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "assistente")
DB_USER = os.getenv("DB_USER", "app_writer")
DB_PASS = os.getenv("DB_PASS", "password")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# --------------------------------------------------------------------
# OpenAI / Responses API (padrão habilitado)
# --------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "o4-mini")  # ou "gpt-5o-reasoning"
USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() not in {"0", "false", "no"}
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))
OPENAI_BASE = os.getenv("OPENAI_BASE", "").strip()  # se usar Enterprise/Proxy

# --------------------------------------------------------------------
# API Interna (Dispatcher → chama a própria API para executar tools)
# --------------------------------------------------------------------

# Base da API interna (em prod, pode ser https://api.odontoapi.com)
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://127.0.0.1:7000").rstrip("/")

# Chave usada pelo dispatcher nas chamadas HTTP internas (cabeçalho x_api_key)
# por padrão reaproveita o APP_SECRET
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")


# JWT
JWT_ISS = os.getenv("JWT_ISS", "nos-assistente")
JWT_AUD = os.getenv("JWT_AUD", "nos-ui")
JWT_KID = os.getenv("JWT_KID", "nos-key-1")
ACCESS_TTL_SEC = int(os.getenv("ACCESS_TTL_SEC", "3600"))
REFRESH_TTL_SEC = int(os.getenv("REFRESH_TTL_SEC", "1209600"))
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
PUBLIC_KEY_PATH = os.getenv("PUBLIC_KEY_PATH")

# CORS
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Cookie Domain
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", ".odontoapi.com")




