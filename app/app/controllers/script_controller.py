import base64
import time
import uuid
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.controllers.auth_controller import verify_api_key
from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger("assistente")
router = APIRouter(prefix="/admin/scripts", tags=["Admin/Scripts"])


class ExecTextRequest(BaseModel):
    content: str | None = None         # código puro (texto)
    content_base64: str | None = None  # código em base64
    timeout: int | None = 30           # segundos


def _decode_content(payload: ExecTextRequest) -> str:
    """
    Prioriza Base64 se presente; cai para texto cru se existir; senão 400.
    """
    if payload.content_base64:
        try:
            return base64.b64decode(payload.content_base64).decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Falha ao decodificar base64: {e}")
    if payload.content and payload.content.strip():
        return payload.content
    raise HTTPException(status_code=400, detail="Nenhum código enviado (use 'content' ou 'content_base64').")


@router.post("/exec_text")
def exec_script_text(payload: ExecTextRequest, _: bool = Depends(verify_api_key)):
    """
    Cria um .py temporário no sandbox de runtime e executa com sys.executable.
    """
    code = _decode_content(payload)
    timeout = payload.timeout or 30

    # sandbox seguro dentro do projeto
    runtime_dir = Path(settings.PROJECT_ROOT_ABS) / "scripts" / "_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    script_path = runtime_dir / f"exectext_{int(time.time())}_{uuid.uuid4().hex[:8]}.py"
    script_path.write_text(code, encoding="utf-8")

    cmd = [sys.executable, str(script_path)]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(settings.PROJECT_ROOT_ABS),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = int((time.time() - t0) * 1000)
        ok = proc.returncode == 0
        logger.info("[scripts] exec: %s (timeout=%ss)", " ".join(cmd), timeout)
        return {
            "ok": ok,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "elapsed_ms": elapsed,
            "script": str(script_path),
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired:
        elapsed = int((time.time() - t0) * 1000)
        logger.error("[scripts] timeout ao executar: %s", " ".join(cmd))
        raise HTTPException(status_code=504, detail=f"Timeout após {elapsed}ms")
    except FileNotFoundError as e:
        logger.error("[scripts] Python não encontrado: %s", e)
        raise HTTPException(status_code=500, detail="Python do ambiente não encontrado (sys.executable inválido?)")
    except Exception as e:
        logger.exception("[scripts] erro ao executar script")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
