# app/app/testing/task_tests.py
"""
Suítes de testes para Tasks/Celery (estrutura base).
Por enquanto, usa apenas testes locais de simulação (sem depender do worker).
Você pode expandir para enfileirar tasks reais e validar status/resultados.
"""

from __future__ import annotations
from typing import List, Dict, Any
from app.testing.runtime import TestOrchestrator

def register_task_tests(orch: TestOrchestrator) -> None:
    """
    Registra suítes de tasks no orquestrador.
    Começa com uma suíte 'smoke' simples; expanda ao integrar com Celery.
    """
    orch.register_suite("smoke", _suite_smoke)

def _suite_smoke(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Suite de smoke que valida a sandbox e simula passos de task.
    Substitua por passos que enfileiram e checam tasks reais futuramente.
    """
    m = TestOrchestrator.make_step

    def _no_op(ctx: Dict[str, Any]) -> Dict[str, Any]:
        # Simula uma "ação" rápida de task local
        return {"note": "no-op task ok", "run_id": ctx["run_id"]}

    return [
        m("fs.mkdir", path="tasks"),
        _no_op,  # callable -> será marcado como passed se não lançar exceção
        m("fs.touch", path="tasks/ok.txt"),
        m("fs.tree", path="tasks"),
        m("fs.delete", path="tasks", recursive=True),
    ]
