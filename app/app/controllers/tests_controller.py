# app/controllers/tests_controller.py
from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.auth_controller import verify_api_key
from app.core.logging_config import get_logger
from app.utils.command_runner import CommandRunner
from app.config.settings import BASE_DIR, DEFAULT_TESTS_DIR

logger = get_logger(__name__)

# Detectado pelo autoloader
router = APIRouter(prefix="/tests", tags=["tests"])

# Runner executando a partir do BASE_DIR (ex.: "/app")
runner = CommandRunner(
    allowed_binaries={"pytest"},
    default_cwd=BASE_DIR,
    default_timeout=300,
)


@router.get("/run")
def run_tests(
    test_path: str = Query(
        default=DEFAULT_TESTS_DIR,
        description="Diretório/arquivo de testes **relativo ao BASE_DIR** (ex.: 'tests' ou 'tests/test_fs.py'). "
                    "Caminhos absolutos também são aceitos."
    ),
    verbose: int = Query(
        default=1, ge=0, le=3,
        description="0=quiet, 1=padrão, 2=-vv, 3=-vv -s"
    ),
    max_output_kb: int = Query(
        default=256, ge=32, le=4096,
        description="Truncagem de stdout/stderr (KB) na resposta."
    ),
    _: None = Depends(verify_api_key),
):
    """
    Executa os testes via pytest partindo do BASE_DIR (ex.: /app).
    - Se `test_path` for relativo, resolvemos contra BASE_DIR → 'tests/abc.py' → '/app/tests/abc.py'.
    - Se `test_path` for absoluto, respeitamos como está.
    """
    full_path = test_path if os.path.isabs(test_path) else os.path.normpath(os.path.join(BASE_DIR, test_path))
    if not os.path.exists(full_path):
        logger.error("[tests_controller] caminho não encontrado: %s", full_path)
        raise HTTPException(status_code=400, detail=f"Caminho de testes não encontrado: {full_path}")

    args: List[str] = ["pytest", test_path, "-rA", "--maxfail=1"]
    if verbose <= 0:
        args.append("-q")
    elif verbose == 2:
        args.append("-vv")
    elif verbose >= 3:
        args.extend(["-vv", "-s"])

    logger.info("[tests_controller] pytest: %s (cwd=%s)", " ".join(args), runner.default_cwd)

    res = runner.run(args, max_output_kb=max_output_kb)

    return {
        "ok": res["ok"],
        "returncode": res["returncode"],
        "args": res["args"],
        "cwd": res["cwd"],                   # deve ser /app
        "resolved_full_path": full_path,     # ex.: /app/tests/abc.py
        "path_param": test_path,
        "stdout": res["stdout"],
        "stderr": res["stderr"],
    }
