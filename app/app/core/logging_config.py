# -*- coding: utf-8 -*-
"""
Configuração central de logging.

- Usa caminhos RELATIVOS ao CWD do processo do container (/app/app).
- Garante criação do diretório de logs antes de anexar o FileHandler.
- Expõe `setup_logging()` (idempotente) e `get_logger()`.

Observações importantes:
- O arquivo de log padrão é `logs/app.log` (relativo). Você pode
  sobrepor via variável de ambiente LOG_FILE.
- O nome do logger padrão é `assistente` (settings.LOGGER_NAME).
"""

from __future__ import annotations

import logging
import logging.handlers
import os

try:
    # Importa as configurações reais do projeto
    from app.config import settings
except Exception:
    # Fallback mínimo para não quebrar em cenários de patch/boot parcial
    class _S:  # pragma: no cover
        LOGGER_NAME = "assistente"
        LOG_FILE = "logs/app.log"

    settings = _S()  # type: ignore[assignment]


def _ensure_log_dir() -> str:
    """
    Garante que o diretório para o arquivo de log exista.
    Retorna o caminho (possivelmente relativo) do arquivo de log.

    - LOG_FILE vem de settings.LOG_FILE; se não existir, usa 'logs/app.log'
    - Cria o diretório pai com os.makedirs(..., exist_ok=True)
    - Em caso de erro de FS, não interrompe a aplicação
    """
    log_file = getattr(settings, "LOG_FILE", "logs/app.log") or "logs/app.log"
    log_dir = os.path.dirname(log_file) or "."
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        # Evita que erro de filesystem impeça o start da API
        pass
    return log_file


def setup_logging() -> logging.Logger:
    """
    Configura o logger base (idempotente) e retorna a instância.

    - Nível: INFO
    - Handlers:
        * StreamHandler (console)
        * RotatingFileHandler (5MB, até 3 backups) -> logs/app.log
    - Se já houver handlers configurados, apenas retorna o logger.
    """
    logger_name = getattr(settings, "LOGGER_NAME", "assistente")
    logger = logging.getLogger(logger_name)

    # Idempotência: se já estiver configurado, retorna
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")

    # Console
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # Arquivo (cria diretório de log se necessário)
    log_file = _ensure_log_dir()
    try:
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        # Se não conseguir abrir arquivo, segue apenas com console
        pass

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Retorna um logger filho após garantir a configuração base.

    Exemplos:
        log = get_logger()             # usa o logger base (assistente)
        log = get_logger(__name__)     # cria/retorna um logger filho
    """
    base = setup_logging()
    return logging.getLogger(name or base.name)
