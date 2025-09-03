# app/app/testing/runtime.py
"""
Runtime de testes (orquestrador genérico com registro de operações)
-------------------------------------------------------------------
Este runtime não conhece mais operações específicas (ex.: fs.*).
As operações são pluggable via `register_ops(namespace_handlers)`.

Contrato do relatório:
{
  "run_id": "...",
  "suite": "...",
  "sandbox_root": "...",
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 123,
  "summary": {"passed": N, "failed": M, "skipped": K},
  "steps": [
    {"name": "<op>:<alvo>", "status": "passed|failed|skipped", "elapsed_ms": 3, "detail": null, "meta": {...}}
  ],
  "ok": true|false,
  "cleanup_performed": true|false  # quando cleanup=True
}
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("assistente")

Step = Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]], str]
OpHandler = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]  # (step, context) -> meta

@dataclass
class StepResult:
    name: str
    status: str               # "passed" | "failed" | "skipped"
    elapsed_ms: int
    detail: Optional[str]
    meta: Dict[str, Any]

def _now_utc_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _ts_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

class TestOrchestrator:
    """
    Orquestrador de suítes/steps de teste com sandbox e registry de operações.

    API principal:
      - register_ops(handlers: dict[str, OpHandler])
      - register_suite(name, steps) / add_suite(...)
      - run_suite(suite, run_name="pytest", cleanup=True)
      - make_step(op, **kwargs)
    """

    def __init__(self, sandbox_base: str = "tmp/test_sandbox") -> None:
        self.sandbox_base = Path(sandbox_base)
        self._suites: Dict[str, Union[List[Step], Callable[[Dict[str, Any]], List[Step]]]] = {}
        self._op_registry: Dict[str, OpHandler] = {}
        _ensure_dir(self.sandbox_base)

    # ---------- Operações (plugin) ----------

    def register_ops(self, handlers: Dict[str, OpHandler]) -> None:
        """
        Registra manipuladores de operações. Chaves são nomes de operação (ex.: "fs.write").
        """
        self._op_registry.update(handlers)
        logger.info("[runtime] %d operações registradas", len(handlers))

    # ---------- Suítes ----------

    def register_suite(self, name: str, steps: Union[List[Step], Callable[[Dict[str, Any]], List[Step]]]) -> None:
        self._suites[name] = steps
        logger.info("[runtime] suíte registrada: %s", name)

    add_suite = register_suite  # alias

    # ---------- Execução ----------

    def run_suite(self, suite: str, run_name: str = "pytest", cleanup: bool = True) -> Dict[str, Any]:
        if suite not in self._suites:
            return {
                "run_id": f"{_ts_run_id()}-{suite}-{run_name}",
                "suite": suite,
                "sandbox_root": str(self.sandbox_base),
                "started_at": _now_utc_iso(),
                "finished_at": _now_utc_iso(),
                "duration_ms": 0,
                "summary": {"passed": 0, "failed": 1, "skipped": 0},
                "steps": [],
                "ok": False,
                "error": f"suíte não registrada: {suite}",
            }

        run_id = f"{_ts_run_id()}-{suite}-{run_name}"
        sandbox_root = self.sandbox_base / f"run-{run_id}"
        _ensure_dir(sandbox_root)

        started_ts = time.time()
        started_iso = _now_utc_iso()
        logger.info("[runtime] iniciando suíte=%s run_id=%s sandbox=%s", suite, run_id, sandbox_root)

        context: Dict[str, Any] = {
            "suite": suite,
            "run_id": run_id,
            "sandbox_root": sandbox_root,
        }

        raw_steps = self._suites[suite]
        steps: List[Step] = raw_steps(context) if callable(raw_steps) else list(raw_steps)  # type: ignore

        results: List[StepResult] = []
        for s in steps:
            results.append(self._execute_step(s, context))

        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")

        finished_iso = _now_utc_iso()
        duration_ms = int((time.time() - started_ts) * 1000)

        report = {
            "run_id": run_id,
            "suite": suite,
            "sandbox_root": str(sandbox_root),
            "started_at": started_iso,
            "finished_at": finished_iso,
            "duration_ms": duration_ms,
            "summary": {"passed": passed, "failed": failed, "skipped": skipped},
            "steps": [r.__dict__ for r in results],
            "ok": (failed == 0),
        }

        if cleanup:
            try:
                shutil.rmtree(sandbox_root, ignore_errors=True)
                report["cleanup_performed"] = True
            except Exception as e:
                logger.warning("[runtime] falha ao limpar sandbox %s: %s", sandbox_root, e)
                report["cleanup_performed"] = False

        logger.info("[runtime] suíte=%s run_id=%s fim: %s", suite, run_id, report["summary"])
        return report

    # ---------- Helpers ----------

    @staticmethod
    def make_step(op: str, **kwargs: Any) -> Dict[str, Any]:
        data = {"op": op}
        data.update(kwargs)
        return data

    # ---------- Execução de Step ----------

    def _execute_step(self, step: Step, context: Dict[str, Any]) -> StepResult:
        t0 = time.time()

        if isinstance(step, str):
            return StepResult(step, "skipped", int((time.time() - t0) * 1000), "step tipo str: ignorado", {})

        if callable(step):
            name = getattr(step, "__name__", "callable")
            try:
                meta = step(context) or {}
                return StepResult(name, "passed", int((time.time() - t0) * 1000), None, meta)
            except Exception as e:
                return StepResult(name, "failed", int((time.time() - t0) * 1000), str(e), {})

        if not isinstance(step, dict) or "op" not in step:
            return StepResult("invalid-step", "failed", int((time.time() - t0) * 1000), "formato inválido", {"step": step})

        op = step["op"]
        handler = self._op_registry.get(op)
        try:
            if handler is None:
                raise ValueError(f"operação não registrada: {op}")
            result = handler(step, context)
            status, detail = "passed", None
        except Exception as e:
            result, status, detail = {}, "failed", str(e)

        name = self._format_step_name(op, step)
        elapsed = int((time.time() - t0) * 1000)
        return StepResult(name, status, elapsed, detail, result)

    @staticmethod
    def _format_step_name(op: str, step: Dict[str, Any]) -> str:
        # tenta deixar legível para fs.* e similares
        if op.endswith(".copy") or op.endswith(".move"):
            return f"{op}:{step.get('src')}->{step.get('dst')}"
        target = step.get("path") or step.get("src") or ""
        return f"{op}:{target}"
