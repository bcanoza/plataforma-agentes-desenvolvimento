# app/api/filesystem/services.py
"""
Serviços de sistema de arquivos - Lógica de negócio.
"""
from __future__ import annotations

import base64
import mimetypes
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Raiz física do projeto
BASE: Path = Path(settings.APP_ROOT).resolve()


class FileSystemService:
    """Serviço para operações de sistema de arquivos."""
    
    @staticmethod
    def _safe_join(rel: str | None) -> Path:
        """
        Resolve um caminho relativo sob a BASE (APP_ROOT) e valida que não
        ocorre path traversal (não sai de BASE).
        """
        rel = rel or ""
        target = (BASE / rel).resolve()
        if not str(target).startswith(str(BASE)):
            raise ValueError("Caminho inválido (fora do APP_ROOT)")
        return target
    
    @staticmethod
    def _list_dir(
        p: Path,
        include_files: bool = True,
        include_dirs: bool = True,
        limit: int = 500,
    ) -> Dict[str, List[str]]:
        """Lista conteúdo de um diretório."""
        try:
            items = list(p.iterdir())
        except (OSError, PermissionError):
            return {"files": [], "directories": []}
        
        files = []
        directories = []
        
        for item in items:
            if len(files) + len(directories) >= limit:
                break
            if item.is_file() and include_files:
                files.append(item.name)
            elif item.is_dir() and include_dirs:
                directories.append(item.name)
        
        return {"files": files, "directories": directories}
    
    @staticmethod
    def _apply_chmod(path: Path, chmod: Optional[str]) -> None:
        """Aplica permissões a um arquivo/diretório."""
        if chmod:
            try:
                mode = int(chmod, 8)
                path.chmod(mode)
            except (ValueError, OSError) as e:
                logger.warning("[fs] falha ao aplicar chmod %s em %s: %s", chmod, path, e)
    
    def list_directory(self, path: Optional[str] = None, limit: int = 500) -> Dict:
        """Lista conteúdo de um diretório."""
        target = self._safe_join(path)
        if not target.exists():
            raise FileNotFoundError("Diretório não encontrado")
        if not target.is_dir():
            raise ValueError("Caminho não é um diretório")
        
        data = self._list_dir(target, limit=limit)
        data["path"] = str(target.relative_to(BASE))
        data["total_files"] = len(data["files"])
        data["total_dirs"] = len(data["directories"])
        
        logger.info("[fs] list path=%s files=%d dirs=%d", target, data["total_files"], data["total_dirs"])
        return data
    
    def get_tree(self, path: Optional[str] = None, depth: int = 2, limit_per_dir: int = 200) -> Dict:
        """Retorna árvore de diretórios."""
        target = self._safe_join(path)
        if not target.exists():
            raise FileNotFoundError("Diretório não encontrado")
        if not target.is_dir():
            raise ValueError("Caminho não é um diretório")
        
        def _build_tree(p: Path, current_depth: int) -> List[Dict]:
            if current_depth <= 0:
                return []
            
            items = []
            try:
                for item in sorted(p.iterdir()):
                    if len(items) >= limit_per_dir:
                        break
                    
                    item_data = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                    }
                    
                    if item.is_file():
                        item_data["size"] = item.stat().st_size
                    elif item.is_dir():
                        children = _build_tree(item, current_depth - 1)
                        if children:
                            item_data["children"] = children
                    
                    items.append(item_data)
            except (OSError, PermissionError):
                pass
            
            return items
        
        tree_items = _build_tree(target, depth)
        total_items = self._count_tree_items(tree_items)
        
        return {
            "path": str(target.relative_to(BASE)),
            "depth": depth,
            "items": tree_items,
            "total_items": total_items,
        }
    
    def _count_tree_items(self, items: List[Dict]) -> int:
        """Conta total de itens na árvore."""
        count = len(items)
        for item in items:
            if item.get("children"):
                count += self._count_tree_items(item["children"])
        return count
    
    def read_file(self, path: str, max_bytes: int = 131072, as_base64: bool = False) -> Dict:
        """Lê conteúdo de um arquivo."""
        target = self._safe_join(path)
        if not target.exists():
            raise FileNotFoundError("Arquivo não encontrado")
        if not target.is_file():
            raise ValueError("Caminho não é arquivo")
        
        size = target.stat().st_size
        mime, _ = mimetypes.guess_type(target.name)
        mime = mime or "application/octet-stream"
        
        likely_text = mime.startswith("text/") or mime in (
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-sh",
            "application/x-python-code",
        )
        
        raw = target.read_bytes()[:max_bytes]
        truncated = size > max_bytes
        
        if as_base64 or not likely_text:
            content_b64 = base64.b64encode(raw).decode("ascii")
            return {
                "path": str(target.relative_to(BASE)),
                "size": size,
                "mime": mime,
                "is_text": False,
                "truncated": truncated,
                "encoding": "base64",
                "content": content_b64,
            }
        
        # Tenta decodificar como texto
        try:
            text = raw.decode("utf-8")
            enc = "utf-8"
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
                enc = "latin-1"
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
                enc = "utf-8 (com erros)"
        
        return {
            "path": str(target.relative_to(BASE)),
            "size": size,
            "mime": mime,
            "is_text": True,
            "truncated": truncated,
            "encoding": enc,
            "content": text,
        }
    
    def write_file(self, path: str, content: str, encoding: str = "text", 
                   append: bool = False, make_dirs: bool = True, backup: bool = False,
                   chmod: Optional[str] = None, max_bytes: int = 5_000_000) -> Dict:
        """Escreve conteúdo em um arquivo."""
        target = self._safe_join(path)
        
        # Converte conteúdo conforme encoding
        if encoding == "base64":
            try:
                raw = base64.b64decode(content, validate=True)
            except Exception as e:
                raise ValueError(f"base64 inválido: {e}")
            mode_label = "binary"
        else:
            try:
                raw = content.encode("utf-8")
            except Exception as e:
                raise ValueError(f"conteúdo inválido (texto): {e}")
            mode_label = "text"
        
        # Limite de tamanho
        if len(raw) > max_bytes:
            raise ValueError(f"payload excede max_bytes={max_bytes} (len={len(raw)})")
        
        # Criação de diretórios pais
        if make_dirs:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error("[fs] falha ao criar diretórios pais de %s: %s", target, e)
                raise ValueError("falha ao criar diretórios pais")
        
        existed = target.exists()
        backup_path = None
        
        # Backup
        if existed and backup:
            ts = time.strftime("%Y%m%d-%H%M%S")
            backup_path = target.with_name(target.name + f".bak-{ts}")
            try:
                backup_path.write_bytes(target.read_bytes())
            except Exception as e:
                logger.warning("[fs] não foi possível criar backup de %s: %s", target, e)
                backup_path = None
        
        # Escrita (append/overwrite)
        try:
            if append:
                with target.open("ab") as f:
                    f.write(raw)
                    bytes_written = len(raw)
            else:
                with target.open("wb") as f:
                    f.write(raw)
                    bytes_written = len(raw)
        except Exception as e:
            logger.error("[fs] erro ao escrever %s: %s", target, e)
            raise ValueError("erro ao escrever arquivo")
        
        # Permissões
        self._apply_chmod(target, chmod)
        
        size_after = target.stat().st_size if target.exists() else 0
        result = {
            "path": str(target.relative_to(BASE)),
            "created": not existed,
            "overwritten": existed and not append,
            "appended": existed and append,
            "bytes_written": bytes_written,
            "size_after": size_after,
            "backup_path": str(backup_path.relative_to(BASE)) if backup_path else None,
            "mode": mode_label,
        }
        
        logger.info(
            "[fs] write path=%s existed=%s append=%s bytes=%s backup=%s mode=%s",
            target, existed, append, bytes_written, bool(backup_path), mode_label
        )
        return result
    
    def create_directory(self, path: str, parents: bool = True, exist_ok: bool = True) -> Dict:
        """Cria um diretório."""
        target = self._safe_join(path)
        
        try:
            target.mkdir(parents=parents, exist_ok=exist_ok)
            return {
                "path": str(target.relative_to(BASE)),
                "created": True,
                "existed": target.exists() and not exist_ok,
            }
        except FileExistsError:
            if not exist_ok:
                raise ValueError("Diretório já existe")
            return {
                "path": str(target.relative_to(BASE)),
                "created": False,
                "existed": True,
            }
        except Exception as e:
            logger.error("[fs] erro ao criar diretório %s: %s", target, e)
            raise ValueError(f"erro ao criar diretório: {e}")
    
    def delete_path(self, path: str, recursive: bool = False) -> Dict:
        """Remove arquivo ou diretório."""
        target = self._safe_join(path)
        
        if not target.exists():
            raise FileNotFoundError("Caminho não encontrado")
        
        try:
            if target.is_file():
                target.unlink()
                return {
                    "path": str(target.relative_to(BASE)),
                    "deleted": True,
                    "type": "file",
                }
            elif target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                    return {
                        "path": str(target.relative_to(BASE)),
                        "deleted": True,
                        "type": "directory",
                        "recursive": True,
                    }
                else:
                    target.rmdir()
                    return {
                        "path": str(target.relative_to(BASE)),
                        "deleted": True,
                        "type": "directory",
                        "recursive": False,
                    }
        except Exception as e:
            logger.error("[fs] erro ao deletar %s: %s", target, e)
            raise ValueError(f"erro ao deletar: {e}")
    
    def move_path(self, source: str, destination: str) -> Dict:
        """Move/renomeia arquivo ou diretório."""
        source_path = self._safe_join(source)
        dest_path = self._safe_join(destination)
        
        if not source_path.exists():
            raise FileNotFoundError("Caminho origem não encontrado")
        
        try:
            shutil.move(str(source_path), str(dest_path))
            return {
                "source": str(source_path.relative_to(BASE)),
                "destination": str(dest_path.relative_to(BASE)),
                "moved": True,
                "type": "directory" if dest_path.is_dir() else "file",
            }
        except Exception as e:
            logger.error("[fs] erro ao mover %s -> %s: %s", source_path, dest_path, e)
            raise ValueError(f"erro ao mover: {e}")
    
    def copy_path(self, source: str, destination: str, recursive: bool = False) -> Dict:
        """Copia arquivo ou diretório."""
        source_path = self._safe_join(source)
        dest_path = self._safe_join(destination)
        
        if not source_path.exists():
            raise FileNotFoundError("Caminho origem não encontrado")
        
        try:
            if source_path.is_file():
                shutil.copy2(str(source_path), str(dest_path))
                return {
                    "source": str(source_path.relative_to(BASE)),
                    "destination": str(dest_path.relative_to(BASE)),
                    "copied": True,
                    "type": "file",
                }
            elif source_path.is_dir():
                if recursive:
                    shutil.copytree(str(source_path), str(dest_path), dirs_exist_ok=True)
                    return {
                        "source": str(source_path.relative_to(BASE)),
                        "destination": str(dest_path.relative_to(BASE)),
                        "copied": True,
                        "type": "directory",
                        "recursive": True,
                    }
                else:
                    raise ValueError("Para copiar diretório, use recursive=True")
        except Exception as e:
            logger.error("[fs] erro ao copiar %s -> %s: %s", source_path, dest_path, e)
            raise ValueError(f"erro ao copiar: {e}")
    
    def touch_file(self, path: str, make_dirs: bool = True) -> Dict:
        """Cria arquivo vazio ou atualiza timestamp."""
        target = self._safe_join(path)
        
        if make_dirs:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error("[fs] falha ao criar diretórios pais de %s: %s", target, e)
                raise ValueError("falha ao criar diretórios pais")
        
        existed = target.exists()
        try:
            target.touch()
            return {
                "path": str(target.relative_to(BASE)),
                "created": not existed,
                "updated": existed,
            }
        except Exception as e:
            logger.error("[fs] erro ao tocar %s: %s", target, e)
            raise ValueError(f"erro ao tocar arquivo: {e}")
