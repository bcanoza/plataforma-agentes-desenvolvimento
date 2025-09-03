# services/integrity_service.py
from __future__ import annotations
import subprocess, sys
from typing import Iterable

from app.core.logging_config import get_logger

class IntegrityService:
    """Serviço de integridade: ações corretivas (ex.: formatar com Black).
    Mantém-se separado do controller para facilitar reuso (CLI, Celery, etc.).
    """

    def __init__(self, logger=None) -> None:
        self.log = logger or get_logger()

    def _to_list(self, targets: Iterable[str] | None) -> list[str]:
        arr = [str(t).strip() for t in (targets or []) if str(t).strip()]
        return arr or ['.']  # padrão: raíz do projeto

    def format_with_black(self, targets: Iterable[str] | None) -> dict:
        """Formata arquivos/diretórios com Black usando o mesmo Python do processo.
        Retorna rc/stdout/stderr. Não levanta exceção para rc != 0 — devolve no payload.
        """
        paths = self._to_list(targets)
        cmd = [sys.executable, '-m', 'black', '--quiet', *paths]
        self.log.info('[integrity] black: %s', ' '.join(cmd))
        try:
            proc = subprocess.run(
                cmd, check=False, capture_output=True, text=True
            )
            return {
                'ok': proc.returncode == 0,
                'rc': proc.returncode,
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'paths': paths,
                'tool': 'black'
            }
        except Exception as e:
            self.log.exception('[integrity] erro executando black')
            return {'ok': False, 'error': str(e), 'paths': paths, 'tool': 'black'}

    def fix_all(self, targets: Iterable[str] | None) -> dict:
        """Pipeline de correções. Hoje: só Black. Amanhã: EOL, trailing spaces, etc."""
        black_res = self.format_with_black(targets)
        ok = bool(black_res.get('ok'))
        return {
            'ok': ok,
            'steps': {
                'black': black_res,
            }
        }
