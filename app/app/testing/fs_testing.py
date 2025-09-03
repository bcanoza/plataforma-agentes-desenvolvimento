# app/app/testing/fs_testing.py
"""
FS Testing (unificado)
---------------------
Arquivo único que reúne:
- Registro de operações de FS (fs.*) para o runtime (plugin)
- Registro das suítes de FS (ex.: 'smoke', 'binary')
- Gancho para integrar testes de tasks relacionados a FS no futuro

Uso típico:
    from app.testing.runtime import TestOrchestrator
    from app.testing.fs_testing import register_fs_ops, register_fs_tests

    orch = TestOrchestrator()
    register_fs_ops(orch)
    register_fs_tests(orch)
    report = orch.run_suite("smoke")
"""

from __future__ import annotations

import base64
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.testing.runtime import TestOrchestrator, OpHandler

# =========================
# 1) Registro de Operações
# =========================

def register_fs_ops(orch: TestOrchestrator) -> None:
    """
    Registra todas as operações `fs.*` no runtime.
    """
    handlers: Dict[str, OpHandler] = {
        "fs.mkdir": _op_fs_mkdir,
        "fs.write": _op_fs_write,
        "fs.append": _op_fs_append,
        "fs.read": _op_fs_read,
        "fs.copy": _op_fs_copy,
        "fs.move": _op_fs_move,
        "fs.touch": _op_fs_touch,
        "fs.tree": _op_fs_tree,
        "fs.download": _op_fs_download,
        "fs.delete": _op_fs_delete,
    }
    orch.register_ops(handlers)

def _sandbox_abs(context: Dict[str, Any], rel: str) -> Path:
    return Path(context["sandbox_root"]) / rel

def _op_fs_mkdir(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    if not rel:
        raise ValueError("fs.mkdir requer 'path'")
    p = _sandbox_abs(context, rel)
    created = not p.exists()
    p.mkdir(parents=True, exist_ok=True)
    return {"path": str(p), "created": created, "chmod_applied": False}

def _op_fs_write(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    content = step.get("content", "")
    mode = step.get("mode", "text")  # "text" | "binary"
    if not rel:
        raise ValueError("fs.write requer 'path'")
    p = _sandbox_abs(context, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()

    if mode == "binary":
        data = base64.b64decode(content) if isinstance(content, str) else bytes(content)
        p.write_bytes(data)
        size_after = p.stat().st_size
        return {
            "path": str(p), "created": not existed, "overwritten": existed, "appended": False,
            "bytes_written": len(data), "size_after": size_after, "backup_path": None, "mode": "binary"
        }
    else:
        s = content if isinstance(content, str) else str(content)
        encoded = s.encode("utf-8")
        p.write_bytes(encoded)
        size_after = p.stat().st_size
        return {
            "path": str(p), "created": not existed, "overwritten": existed, "appended": False,
            "bytes_written": len(encoded), "size_after": size_after, "backup_path": None, "mode": "text"
        }

def _op_fs_append(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    content = step.get("content", "")
    if not rel:
        raise ValueError("fs.append requer 'path'")
    p = _sandbox_abs(context, rel)
    if not p.exists():
        raise FileNotFoundError(f"arquivo inexistente para append: {rel}")

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup = p.parent / f"{p.name}.bak-{ts}"
    shutil.copy2(p, backup)

    s = content if isinstance(content, str) else str(content)
    encoded = s.encode("utf-8")
    with p.open("ab") as f:
        f.write(encoded)

    size_after = p.stat().st_size
    return {
        "path": str(p), "created": False, "overwritten": False, "appended": True,
        "bytes_written": len(encoded), "size_after": size_after, "backup_path": str(backup), "mode": "text"
    }

def _op_fs_read(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    if not rel:
        raise ValueError("fs.read requer 'path'")
    p = _sandbox_abs(context, rel)
    if not p.exists():
        raise FileNotFoundError(f"arquivo inexistente para leitura: {rel}")
    b = p.read_bytes()
    return {
        "path": str(p), "size": len(b), "mime": "application/octet-stream",
        "is_text": False, "truncated": False, "encoding": "base64", "content": base64.b64encode(b).decode("ascii")
    }

def _op_fs_copy(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    src_rel = step.get("src") or step.get("path")
    dst_rel = step.get("dst")
    if not src_rel or not dst_rel:
        raise ValueError("fs.copy requer 'src' e 'dst'")
    src = _sandbox_abs(context, src_rel)
    dst = _sandbox_abs(context, dst_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return {"src": str(src), "dst": str(dst), "is_dir": True, "is_file": False, "overwrote": True, "preserve_times": True}
    shutil.copy2(src, dst)
    return {"src": str(src), "dst": str(dst), "is_dir": False, "is_file": True, "overwrote": True, "preserve_times": True}

def _op_fs_move(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    src_rel = step.get("src") or step.get("path")
    dst_rel = step.get("dst")
    if not src_rel or not dst_rel:
        raise ValueError("fs.move requer 'src' e 'dst'")
    src = _sandbox_abs(context, src_rel)
    dst = _sandbox_abs(context, dst_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))
    return {"src": str(src), "dst": str(dst), "is_dir": src.is_dir(), "is_file": src.is_file(), "overwrote": True}

def _op_fs_touch(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    if not rel:
        raise ValueError("fs.touch requer 'path'")
    p = _sandbox_abs(context, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.touch(exist_ok=True)
    return {"path": str(p), "touched": True, "chmod_applied": False, "existed": existed}

def _op_fs_tree(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    if not rel:
        raise ValueError("fs.tree requer 'path'")
    root = _sandbox_abs(context, rel)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"diretório inválido para tree: {rel}")

    def build(node: Path) -> Dict[str, Any]:
        if node.is_dir():
            return {
                "name": node.name + "/",
                "type": "dir",
                "children": [build(child) for child in sorted(node.iterdir(), key=lambda p: p.name)],
            }
        return {"name": node.name, "type": "file"}

    return {"name": root.name + "/", "type": "dir", "children": [build(c) for c in sorted(root.iterdir(), key=lambda p: p.name)], "root": str(root)}

def _op_fs_download(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    if not rel:
        raise ValueError("fs.download requer 'path'")
    p = _sandbox_abs(context, rel)
    if not p.exists():
        raise FileNotFoundError(f"arquivo inexistente para download: {rel}")
    return {"result_type": "FileResponse"}

def _op_fs_delete(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    rel = step.get("path")
    recursive = bool(step.get("recursive", True))
    if not rel:
        raise ValueError("fs.delete requer 'path'")
    p = _sandbox_abs(context, rel)
    if not p.exists():
        return {"path": str(p), "removed": False, "type": None, "recursive": recursive}
    if p.is_dir():
        if recursive:
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.rmdir()
        return {"path": str(p), "removed": True, "type": "dir", "recursive": recursive}
    p.unlink(missing_ok=True)
    return {"path": str(p), "removed": True, "type": "file", "recursive": recursive}

# =========================
# 2) Suítes de Testes (FS)
# =========================

PNG_1X1_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)

def register_fs_tests(orch: TestOrchestrator) -> None:
    """Registra as suítes de FS no orquestrador (requer `register_fs_ops` antes)."""
    orch.register_suite("smoke", _suite_smoke)
    orch.register_suite("binary", _suite_binary)

def _suite_smoke(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    m = TestOrchestrator.make_step
    return [
        m("fs.mkdir", path="docs"),
        m("fs.write", path="docs/NOTAS.md", content="linha 1\n", mode="text"),
        m("fs.append", path="docs/NOTAS.md", content="\n+ outra"),
        m("fs.read", path="docs/NOTAS.md"),
        m("fs.copy", src="docs/NOTAS.md", dst="docs/NOTAS-copy.md"),
        m("fs.move", src="docs/NOTAS-copy.md", dst="docs/NOTAS-old.md"),
        m("fs.touch", path="docs/vazio.txt"),
        m("fs.tree", path="docs"),
        m("fs.download", path="docs/NOTAS-old.md"),
        m("fs.delete", path="docs", recursive=True),
    ]

def _suite_binary(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    m = TestOrchestrator.make_step
    return [
        m("fs.mkdir", path="bin"),
        m("fs.write", path="bin/pixel.png", content=PNG_1X1_B64, mode="binary"),
        m("fs.read", path="bin/pixel.png"),
        m("fs.copy", src="bin/pixel.png", dst="bin/pixel-copy.png"),
        m("fs.move", src="bin/pixel-copy.png", dst="bin/pixel-old.png"),
        m("fs.tree", path="bin"),
        m("fs.delete", path="bin", recursive=True),
    ]

# =========================
# 3) (Opcional) Gancho para tasks relacionadas a FS
# =========================

def register_fs_task_suites(orch: TestOrchestrator) -> None:
    """
    Exemplo de gancho para, no futuro, enfileirar tasks de FS (via Celery) e validar por aqui.
    Atualmente não registra nenhuma suite adicional.
    """
    pass
