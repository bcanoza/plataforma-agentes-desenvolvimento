from __future__ import annotations
import os
import io
import json
import sys
import py_compile
import importlib.util
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Iterable, Optional

try:
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    from app.config import settings as _settings
    logger = logging.getLogger(getattr(_settings, "LOGGER_NAME", "assistente"))

class DiagnosticsService:
    """Serviço de diagnóstico estático (somente leitura).

    Checks disponíveis (nomes para `checks`):
      - exists
      - syntax
      - encoding_utf8
      - file_size
      - forbidden_outside_root
      - trailing_newline
      - line_endings
      - mixed_indentation
      - import_resolvable
      - ruff                (opcional; requer pacote ruff)
      - black               (opcional; requer pacote black)

    Opções suportadas em `**opts`:
      - root: str | Path  -> raiz segura (padrão: settings.PROJECT_ROOT_ABS)
      - max_bytes: int    -> limite para file_size (padrão: 1 MiB)
      - ruff_args: list[str] -> argumentos extras para ruff
      - black_args: list[str] -> argumentos extras para black
    """

    def __init__(self, root: Optional[Path] = None):
        from app.config import settings
        self.settings = settings
        self.root = Path(root or settings.PROJECT_ROOT_ABS).resolve()

    # --------------------------- helpers ---------------------------
    def _safe_path(self, path: str | os.PathLike) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = (self.root / p).resolve()
        return p

    def _is_within_root(self, p: Path) -> bool:
        try:
            p.resolve().relative_to(self.root)
            return True
        except Exception:
            return False

    # ----------------------------- checks --------------------------
    def check_exists(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        exists = p.exists()
        return {"file": str(path), "abs": str(p), "exists": exists}

    def check_syntax(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "syntax_ok": True, "error": None}
        if p.is_file():
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                res["syntax_ok"] = False
                res["error"] = str(e)
            except Exception as e:
                res["syntax_ok"] = False
                res["error"] = f"unexpected: {e}"
        else:
            res["syntax_ok"] = False
            res["error"] = "not a file"
        return res

    def check_encoding_utf8(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "encoding_utf8": True, "error": None}
        if p.is_file():
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                raw.decode("utf-8")
            except UnicodeDecodeError as e:
                res["encoding_utf8"] = False
                res["error"] = f"unicode: {e}"
            except Exception as e:
                res["encoding_utf8"] = False
                res["error"] = f"unexpected: {e}"
        else:
            res["encoding_utf8"] = False
            res["error"] = "not a file"
        return res

    def check_file_size(self, path: str, *, max_bytes: int = 1_048_576) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "size_ok": True, "size": None, "max": max_bytes}
        if p.is_file():
            try:
                size = p.stat().st_size
                res["size"] = size
                if size > max_bytes:
                    res["size_ok"] = False
            except Exception as e:
                res["size_ok"] = False
                res["error"] = f"stat: {e}"
        else:
            res["size_ok"] = False
            res["error"] = "not a file"
        return res

    def check_forbidden_outside_root(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        inside = self._is_within_root(p)
        return {"file": str(path), "abs": str(p), "inside_root": inside}

    def check_trailing_newline(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "trailing_newline": True}
        if p.is_file():
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                res["trailing_newline"] = raw.endswith(b"\n")
            except Exception as e:
                res["trailing_newline"] = False
                res["error"] = f"read: {e}"
        else:
            res["trailing_newline"] = False
            res["error"] = "not a file"
        return res

    def check_line_endings(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "lf_only": True}
        if p.is_file():
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                if b"\r\n" in raw:
                    res["lf_only"] = False
                    res["has_crlf"] = True
            except Exception as e:
                res["lf_only"] = False
                res["error"] = f"read: {e}"
        else:
            res["lf_only"] = False
            res["error"] = "not a file"
        return res

    def check_mixed_indentation(self, path: str, *, sample_lines: int = 200) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "mixed_indentation": False}
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [next(f, "") for _ in range(sample_lines)]
                has_tab = any(line.startswith("\t") for line in lines)
                has_space = any(line.startswith(" ") for line in lines)
                res["mixed_indentation"] = bool(has_tab and has_space)
            except Exception as e:
                res["error"] = f"read: {e}"
        else:
            res["error"] = "not a file"
        return res

    def check_import_resolvable(self, path: str) -> Dict[str, Any]:
        p = self._safe_path(path)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "import_resolvable": True}
        if p.is_file():
            try:
                spec = importlib.util.spec_from_file_location(p.stem, str(p))
                if spec is None or spec.loader is None:
                    res["import_resolvable"] = False
            except Exception as e:
                res["import_resolvable"] = False
                res["error"] = f"spec: {e}"
        else:
            res["import_resolvable"] = False
            res["error"] = "not a file"
        return res

    # ---------- novos: linters (opcionais) ----------
    def check_ruff_lint(self, path: str, *, extra_args: Optional[list[str]] = None) -> Dict[str, Any]:
        p = self._safe_path(path)
        cmd = [sys.executable, '-m', 'ruff', 'check', '--output-format', 'json', str(p)]
        if extra_args:
            cmd.extend(extra_args)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "tool": "ruff", "available": True}
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root), timeout=60)
            # ruff sai com rc>0 quando há findings; não tratamos como erro
            data = cp.stdout.strip()
            parsed = json.loads(data) if data else []
            res.update({"findings": parsed, "returncode": cp.returncode})
        except FileNotFoundError:
            res.update({"available": False, "note": "ruff não instalado (pip install ruff)"})
        except ModuleNotFoundError:
            res.update({"available": False, "note": "módulo ruff não encontrado (pip install ruff)"})
        except Exception as e:
            res.update({"error": str(e)})
        return res

    def check_black_format(self, path: str, *, extra_args: Optional[list[str]] = None) -> Dict[str, Any]:
        p = self._safe_path(path)
        cmd = [sys.executable, '-m', 'black', '--check', '--diff', str(p)]
        if extra_args:
            cmd.extend(extra_args)
        res: Dict[str, Any] = {"file": str(path), "abs": str(p), "tool": "black", "available": True}
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root), timeout=60)
            # black --check retorna 0 (formatado) ou 1 (requer formatação)
            res.update({"returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr})
            res["formatted_ok"] = (cp.returncode == 0)
        except FileNotFoundError:
            res.update({"available": False, "note": "black não instalado (pip install black)"})
        except ModuleNotFoundError:
            res.update({"available": False, "note": "módulo black não encontrado (pip install black)"})
        except Exception as e:
            res.update({"error": str(e)})
        return res

    # ----------------------------- runner --------------------------
    def run_all(
        self,
        paths: List[str],
        checks: Optional[Iterable[str]] = None,
        **opts: Any,
    ) -> List[Dict[str, Any]]:
        """Executa os checks em `paths`.
        - `checks`: subset opcional. Se None, roda todos.
        - `opts`: opções por check (ex.: max_bytes=2_097_152, ruff_args=[...])
        """
        available = {
            "exists": self.check_exists,
            "syntax": self.check_syntax,
            "encoding_utf8": self.check_encoding_utf8,
            "file_size": lambda p: self.check_file_size(p, max_bytes=int(opts.get("max_bytes", 1_048_576))),
            "forbidden_outside_root": self.check_forbidden_outside_root,
            "trailing_newline": self.check_trailing_newline,
            "line_endings": self.check_line_endings,
            "mixed_indentation": self.check_mixed_indentation,
            "import_resolvable": self.check_import_resolvable,
            "ruff": lambda p: self.check_ruff_lint(p, extra_args=opts.get("ruff_args")),
            "black": lambda p: self.check_black_format(p, extra_args=opts.get("black_args")),
        }
        order = [
            "exists",
            "forbidden_outside_root",
            "file_size",
            "encoding_utf8",
            "syntax",
            "line_endings",
            "trailing_newline",
            "mixed_indentation",
            "import_resolvable",
            "ruff",
            "black",
        ]
        if checks:
            chosen = [c for c in order if c in set(checks)]
        else:
            chosen = order

        results: List[Dict[str, Any]] = []
        for path in paths:
            for c in chosen:
                try:
                    results.append(available[c](path))
                except Exception as e:
                    results.append({"file": path, "check": c, "error": str(e)})
        return results
