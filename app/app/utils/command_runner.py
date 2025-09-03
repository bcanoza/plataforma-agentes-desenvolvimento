# app/utils/command_runner.py
"""
Command Runner
--------------
Utilitário padronizado e seguro para executar processos externos.

Recursos:
- shell desativado (seguro) e tokenização via shlex.split quando cmd é string;
- allowlist de binários permitidos (defensivo);
- timeout configurável;
- captura de stdout/stderr com truncagem opcional (KB);
- controle de CWD/ENV por execução e defaults no construtor;
- retorno estruturado em dict (ok, returncode, args, stdout, stderr, cwd).

Uso típico:
    from app.utils.command_runner import CommandRunner
    runner = CommandRunner(allowed_binaries={"pytest"}, default_cwd="/app")
    res = runner.run(["pytest", "tests", "-q"])
    print(res["ok"], res["stdout"])
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Union

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CommandRunner:
    """
    Executor centralizado de comandos externos.

    Args:
        allowed_binaries: conjunto de comandos/binários permitidos
                          (ex.: {"pytest", "alembic", "pg_dump"}).
        default_cwd: diretório padrão de execução (ex.: "/app").
        default_env: env base (merge com env passado em cada execução).
        default_timeout: timeout padrão em segundos (default 300).
    """
    allowed_binaries: Optional[Iterable[str]] = field(default_factory=lambda: {"pytest", "echo", "ls", "python"})
    default_cwd: Optional[str] = None
    default_env: Optional[Mapping[str, str]] = None
    default_timeout: int = 300

    @staticmethod
    def _normalize_cmd(cmd: Union[str, Sequence[str]]) -> List[str]:
        if isinstance(cmd, str):
            return shlex.split(cmd)
        return list(cmd)

    def _is_allowed(self, cmd: Sequence[str]) -> bool:
        if not cmd:
            return False
        if not self.allowed_binaries:
            return True
        head = cmd[0]
        head_name = os.path.basename(head)
        allowed = set(self.allowed_binaries)
        return head in allowed or head_name in allowed

    @staticmethod
    def _truncate(text: str, max_output_kb: Optional[int]) -> str:
        if max_output_kb is None:
            return text or ""
        limit = max(1, int(max_output_kb)) * 1024
        data = (text or "").encode("utf-8", errors="replace")
        return data[:limit].decode("utf-8", errors="replace")

    def run(
        self,
        cmd: Union[str, Sequence[str]],
        *,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        text: bool = True,
        max_output_kb: Optional[int] = 512,
        check: bool = False,
    ) -> Dict[str, object]:
        """
        Executa um comando e retorna um dicionário estruturado.

        Returns:
            {
              "ok": bool,
              "returncode": int|None,
              "args": "string para logs",
              "stdout": str,
              "stderr": str,
              "cwd": str|None,
              "error": str|None
            }
        """
        args = self._normalize_cmd(cmd)
        run_cwd = cwd or self.default_cwd
        run_timeout = timeout if timeout is not None else self.default_timeout

        if not args:
            return {"ok": False, "error": "comando vazio", "returncode": None, "args": "", "stdout": "", "stderr": "", "cwd": run_cwd}

        if not self._is_allowed(args):
            quoted = " ".join(shlex.quote(a) for a in args)
            logger.warning("[command_runner] comando bloqueado: %s", quoted)
            return {"ok": False, "error": f"comando não permitido: {args[0]}", "returncode": None, "args": quoted, "stdout": "", "stderr": "", "cwd": run_cwd}

        # Merge de env (default_env < env)
        if self.default_env:
            run_env = dict(os.environ)
            run_env.update(self.default_env)
            if env:
                run_env.update(env)
        else:
            run_env = dict(os.environ)
            if env:
                run_env.update(env)

        quoted = " ".join(shlex.quote(a) for a in args)
        logger.info("[command_runner] exec: %s (cwd=%s, timeout=%ss)", quoted, run_cwd, run_timeout)

        try:
            proc = subprocess.run(
                args,
                cwd=run_cwd,
                env=run_env,
                capture_output=capture_output,
                text=text,
                timeout=run_timeout,
                check=check,
            )
            out = proc.stdout if capture_output and text else ""
            err = proc.stderr if capture_output and text else ""
            result = {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "args": quoted,
                "stdout": self._truncate(out, max_output_kb),
                "stderr": self._truncate(err, max_output_kb),
                "cwd": run_cwd,
                "error": None,
            }
            if proc.returncode != 0:
                logger.warning("[command_runner] rc=%s stderr=%s", proc.returncode, result["stderr"])
            else:
                logger.info("[command_runner] rc=%s", proc.returncode)
            return result

        except subprocess.TimeoutExpired as e:
            logger.error("[command_runner] timeout: %s", e)
            return {"ok": False, "error": "timeout", "returncode": None, "args": quoted, "stdout": self._truncate(getattr(e, "stdout", "") or "", max_output_kb), "stderr": self._truncate(getattr(e, "stderr", "") or "", max_output_kb), "cwd": run_cwd}

        except FileNotFoundError as e:
            logger.error("[command_runner] binário não encontrado: %s", e)
            return {"ok": False, "error": f"binário não encontrado: {e}", "returncode": None, "args": quoted, "stdout": "", "stderr": str(e), "cwd": run_cwd}

        except Exception as e:
            logger.exception("[command_runner] erro inesperado")
            return {"ok": False, "error": f"erro inesperado: {e}", "returncode": None, "args": quoted, "stdout": "", "stderr": str(e), "cwd": run_cwd}
