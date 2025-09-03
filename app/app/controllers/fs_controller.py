# app/controllers/fs_controller.py
"""
Filesystem Controller
----------------------
Endpoints administrativos para inspecionar e modificar arquivos e diretórios
dentro do `APP_ROOT` configurado em `app.config.settings`.

⚠️ Segurança:
- Todas as operações são confinadas ao APP_ROOT por meio de `_safe_join`, que bloqueia
  path traversal. Sempre forneça caminhos **relativos** ao APP_ROOT.
- Todos os endpoints exigem autenticação por API Key via `verify_api_key` e usam o
  header **x_api_key** (com underscore). Ex.: `-H 'x_api_key: nos123456'`.

Endpoints:
- GET  /fs/ls         → lista conteúdo (não-recursivo) de um diretório.
- GET  /fs/tree       → retorna árvore (recursivo com profundidade limitada).
- GET  /fs/read       → lê conteúdo de um arquivo (texto/b64).
- POST /fs/write      → cria/atualiza arquivo (texto ou binário base64, append, backup, chmod).
- POST /fs/mkdir      → cria diretório (com pais opcionais).
- DELETE /fs/delete   → remove arquivo ou diretório (opcionalmente recursivo).
- POST /fs/move       → mover/renomear arquivo ou diretório.
- POST /fs/copy       → copiar arquivo ou diretório.
- POST /fs/touch      → criar arquivo vazio / atualizar mtime.
- GET  /fs/download   → baixar um arquivo como attachment/inline.

Parâmetros comuns:
- `path` é sempre RELATIVO ao APP_ROOT.
- Limites (`limit`, `limit_per_dir`, `max_bytes`) protegem contra respostas/gravações enormes.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.controllers.auth_controller import verify_api_key  # reutiliza sua autenticação
from app.core.logging_config import get_logger

# Logger padrão do projeto
logger = get_logger(__name__)

# Router com proteção por API Key (x_api_key)
router = APIRouter(
    prefix="/fs",
    tags=["Filesystem"],
    dependencies=[Depends(verify_api_key)],
)

# Raiz física do projeto (no container deve ser algo como /app/app)
BASE: Path = Path(settings.APP_ROOT).resolve()


# =============================================================================
# Helpers internos
# =============================================================================
def _safe_join(rel: str | None) -> Path:
    """
    Resolve um caminho relativo sob a BASE (APP_ROOT) e valida que não
    ocorre path traversal (não sai de BASE).

    Args:
        rel: caminho relativo (pode ser None ou vazio → BASE).

    Returns:
        Path absoluto seguro dentro de BASE.

    Raises:
        HTTPException 400 se o caminho sair de BASE.
    """
    rel = rel or ""
    target = (BASE / rel).resolve()
    if not str(target).startswith(str(BASE)):
        raise HTTPException(status_code=400, detail="Caminho inválido (fora do APP_ROOT).")
    return target


def _list_dir(
    p: Path,
    include_files: bool = True,
    include_dirs: bool = True,
    limit: int = 500,
) -> Dict[str, List[str]]:
    """
    Lista conteúdo imediato (não-recursivo) de um diretório.

    Args:
        p: diretório alvo (absoluto, já validado).
        include_files: inclui arquivos na resposta.
        include_dirs: inclui subdiretórios na resposta.
        limit: máximo de itens (direórios + arquivos).

    Returns:
        dicionário com path relativo, listas 'dirs' e 'files'.

    Raises:
        HTTPException 400 se `p` não for diretório.
    """
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="Caminho não é diretório.")

    files, dirs, count = [], [], 0
    for entry in sorted(p.iterdir(), key=lambda e: e.name):
        if count >= limit:
            break
        if entry.is_dir() and include_dirs:
            dirs.append(entry.name + "/")
            count += 1
        elif entry.is_file() and include_files:
            files.append(entry.name)
            count += 1

    return {
        "path": str(p.relative_to(BASE) if p != BASE else "."),
        "dirs": dirs,
        "files": files,
    }


def _tree(p: Path, depth: int, limit_per_dir: int) -> Dict:
    """
    Retorna estrutura hierárquica de diretórios/arquivos a partir de `p`.

    Args:
        p: caminho inicial (absoluto, validado).
        depth: profundidade máxima (0 = só o nó atual).
        limit_per_dir: máximo de itens listados por diretório.

    Returns:
        dicionário com 'name', 'type' e opcionalmente 'children'.
    """
    node = {"name": p.name + ("/" if p.is_dir() else ""), "type": "dir" if p.is_dir() else "file"}
    if not p.is_dir() or depth <= 0:
        return node

    children, count = [], 0
    for entry in sorted(p.iterdir(), key=lambda e: e.name):
        if count >= limit_per_dir:
            break
        children.append(_tree(entry, depth - 1, limit_per_dir))
        count += 1

    node["children"] = children
    return node


def _apply_chmod(target: Path, chmod: str | int | None) -> None:
    """
    Aplica chmod no arquivo/diretório alvo, se fornecido.

    Args:
        target: caminho absoluto (validado).
        chmod: str octal (ex.: "0644") ou int (ex.: 420). None desabilita.

    Observação:
        Falhas de chmod geram WARNING mas não abortam a operação.
    """
    if chmod is None:
        return
    try:
        mode = int(str(chmod), 8) if isinstance(chmod, str) else int(chmod)
        os.chmod(target, mode)
    except Exception as e:
        logger.warning("[fs] chmod falhou em %s (chmod=%s): %s", target, chmod, e)


# =============================================================================
# Modelos (payloads)
# =============================================================================
class FileWriteRequest(BaseModel):
    """
    Payload para criação/atualização de arquivo.

    Atributos:
        path: caminho RELATIVO ao APP_ROOT (ex.: "docs/README.md").
        content: conteúdo a gravar (texto UTF-8 ou base64 conforme `encoding`).
        encoding: "text" (padrão) ou "base64" para binários.
        append: se True, faz append; se False, sobrescreve.
        make_dirs: cria diretórios pais automaticamente se necessário.
        backup: se True e o arquivo existir, gera backup `.bak-YYYYMMDD-HHMMSS`.
        chmod: permissões pós-escrita (str octal, ex.: "0644", ou int).
        max_bytes: limite de bytes aceitos (proteção contra uploads grandes).
    """
    path: str = Field(..., min_length=1)
    content: str = Field(..., description="Texto (UTF-8) ou base64, conforme 'encoding'")
    encoding: str = Field(default="text", pattern="^(text|base64)$")
    append: bool = False
    make_dirs: bool = True
    backup: bool = True
    chmod: str | int | None = Field(default=None, description='Ex.: "0644" ou 420')
    max_bytes: int = Field(default=5_000_000, ge=1, le=50_000_000)


class MkdirRequest(BaseModel):
    """
    Payload para criação de diretório.

    Atributos:
        path: caminho RELATIVO ao APP_ROOT (ex.: "data/exports").
        parents: se True, cria todos os pais.
        exist_ok: se True, não falha se já existir.
        chmod: permissões (opcional) aplicadas após criar.
    """
    path: str = Field(..., min_length=1)
    parents: bool = True
    exist_ok: bool = True
    chmod: str | int | None = Field(default=None)


class DeleteRequest(BaseModel):
    """
    Payload para remoção de arquivo/diretório.

    Atributos:
        path: caminho RELATIVO ao APP_ROOT a ser removido.
        recursive: se True e for diretório, remove recursivamente (use com cuidado).
        missing_ok: se True, não falha se o caminho não existir (idempotente).
    """
    path: str = Field(..., min_length=1)
    recursive: bool = False
    missing_ok: bool = True


class MoveRequest(BaseModel):
    """
    Payload para mover/renomear arquivos ou diretórios dentro do APP_ROOT.

    Atributos:
        src: caminho RELATIVO de origem (arquivo ou diretório).
        dst: caminho RELATIVO de destino (novo nome/local).
        overwrite: se True, permite sobrescrever o destino se já existir.
        make_dirs: se True, cria diretórios pais do destino se necessário.
    """
    src: str = Field(..., min_length=1)
    dst: str = Field(..., min_length=1)
    overwrite: bool = False
    make_dirs: bool = True


class CopyRequest(BaseModel):
    """
    Payload para copiar arquivos ou diretórios dentro do APP_ROOT.

    Atributos:
        src: caminho RELATIVO de origem.
        dst: caminho RELATIVO de destino.
        overwrite: se True, remove destino existente antes de copiar.
        make_dirs: se True, cria diretórios pais do destino.
        preserve_times: se True, preserva timestamps/metadata quando possível.
    """
    src: str = Field(..., min_length=1)
    dst: str = Field(..., min_length=1)
    overwrite: bool = False
    make_dirs: bool = True
    preserve_times: bool = True


class TouchRequest(BaseModel):
    """
    Payload para criar arquivo vazio ou atualizar mtime (sem alterar conteúdo).

    Atributos:
        path: caminho RELATIVO do arquivo.
        make_dirs: se True, cria diretórios pais.
        exist_ok: se False, falha se já existir; se True, apenas atualiza mtime.
        chmod: permissões após tocar (opcional).
    """
    path: str = Field(..., min_length=1)
    make_dirs: bool = True
    exist_ok: bool = True
    chmod: str | int | None = Field(default=None)


# =============================================================================
# Endpoints
# =============================================================================
@router.get("/ls")
def fs_ls(
    path: str | None = Query(default=None, description="Relativo ao APP_ROOT (ex.: 'app/controllers')"),
    include_files: bool = True,
    include_dirs: bool = True,
    limit: int = Query(500, ge=1, le=5000),
):
    """
    Lista conteúdo (não-recursivo) de um diretório.

    Query:
        path, include_files, include_dirs, limit
    """
    target = _safe_join(path)
    out = _list_dir(target, include_files=include_files, include_dirs=include_dirs, limit=limit)
    logger.info("[fs] ls path=%s ok", target)
    return out


@router.get("/tree")
def fs_tree(
    path: str | None = Query(default=None, description="Relativo ao APP_ROOT"),
    depth: int = Query(2, ge=0, le=10, description="Profundidade da árvore (0=apenas o nó)"),
    limit_per_dir: int = Query(200, ge=1, le=2000, description="Máximo de itens por diretório"),
):
    """
    Retorna a árvore de diretórios e arquivos a partir de `path`.
    """
    target = _safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Caminho não encontrado.")
    data = _tree(target, depth=depth, limit_per_dir=limit_per_dir)
    data["root"] = str(target.relative_to(BASE)) if target != BASE else "."
    logger.info("[fs] tree path=%s depth=%s ok", target, depth)
    return data


@router.get("/read")
def fs_read(
    path: str = Query(..., description="Caminho RELATIVO (ex.: 'app/main.py')"),
    max_bytes: int = Query(131072, ge=1, le=5_000_000, description="Máximo de bytes retornados (default 128 KiB)"),
    as_base64: bool = Query(False, description="Se True, retorna conteúdo em base64"),
):
    """
    Lê o conteúdo de um arquivo sob APP_ROOT (texto ou base64).

    Regras:
    - Bloqueia sair do APP_ROOT.
    - Limita o tamanho (max_bytes).
    - Heurística simples para decidir se é texto, com fallback para base64.
    """
    target = _safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Caminho não é arquivo.")

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
        logger.info("[fs] read (b64) path=%s size=%s truncated=%s", target, size, truncated)
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
            # Fallback final para base64
            content_b64 = base64.b64encode(raw).decode("ascii")
            logger.info("[fs] read (fallback b64) path=%s size=%s truncated=%s", target, size, truncated)
            return {
                "path": str(target.relative_to(BASE)),
                "size": size,
                "mime": mime,
                "is_text": False,
                "truncated": truncated,
                "encoding": "base64",
                "content": content_b64,
            }

    logger.info("[fs] read path=%s size=%s truncated=%s", target, size, truncated)
    return {
        "path": str(target.relative_to(BASE)),
        "size": size,
        "mime": mime,
        "is_text": True,
        "truncated": truncated,
        "encoding": enc,
        "content": text,
    }


@router.post("/write")
def fs_write(payload: FileWriteRequest):
    """
    Cria/atualiza um arquivo sob APP_ROOT.

    Regras:
    - `encoding` "text" ou "base64".
    - `append=True` adiciona ao final; caso contrário, sobrescreve.
    - `make_dirs=True` cria os diretórios pais se necessário.
    - `backup=True` gera `arquivo.bak-YYYYMMDD-HHMMSS` antes de sobrescrever.
    - `chmod` aplica permissões (ex.: "0644").

    Retorna metadados da operação.
    """
    target = _safe_join(payload.path)

    # Converte conteúdo conforme encoding
    if payload.encoding == "base64":
        try:
            raw = base64.b64decode(payload.content, validate=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"base64 inválido: {e}")
        mode_label = "binary"
    else:
        try:
            raw = payload.content.encode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"conteúdo inválido (texto): {e}")
        mode_label = "text"

    # Limite de tamanho
    if len(raw) > payload.max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"payload excede max_bytes={payload.max_bytes} (len={len(raw)})",
        )

    # Criação de diretórios pais
    if payload.make_dirs:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("[fs] falha ao criar diretórios pais de %s: %s", target, e)
            raise HTTPException(status_code=500, detail="falha ao criar diretórios pais")

    existed = target.exists()
    backup_path = None

    # Backup
    if existed and payload.backup:
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = target.with_name(target.name + f".bak-{ts}")
        try:
            backup_path.write_bytes(target.read_bytes())
        except Exception as e:
            logger.warning("[fs] não foi possível criar backup de %s: %s", target, e)
            backup_path = None

    # Escrita (append/overwrite)
    try:
        if payload.append:
            with target.open("ab") as f:
                f.write(raw)
                bytes_written = len(raw)
        else:
            with target.open("wb") as f:
                f.write(raw)
                bytes_written = len(raw)
    except Exception as e:
        logger.error("[fs] erro ao escrever %s: %s", target, e)
        raise HTTPException(status_code=500, detail="erro ao escrever arquivo")

    # Permissões
    _apply_chmod(target, payload.chmod)

    size_after = target.stat().st_size if target.exists() else 0
    result = {
        "path": str(target.relative_to(BASE)),
        "created": not existed,
        "overwritten": existed and not payload.append,
        "appended": existed and payload.append,
        "bytes_written": bytes_written,
        "size_after": size_after,
        "backup_path": str(backup_path.relative_to(BASE)) if backup_path else None,
        "mode": mode_label,
    }
    logger.info(
        "[fs] write path=%s existed=%s append=%s bytes=%s backup=%s mode=%s",
        target, existed, payload.append, bytes_written, bool(backup_path), mode_label
    )
    return result


@router.post("/mkdir")
def fs_mkdir(payload: MkdirRequest):
    """
    Cria um diretório sob APP_ROOT.

    Comportamento:
    - `parents=True` cria diretórios pais (padrão).
    - `exist_ok=True` não falha se já existir.
    - `chmod` aplica permissões após a criação.
    """
    target = _safe_join(payload.path)
    try:
        target.mkdir(parents=payload.parents, exist_ok=payload.exist_ok)
    except FileExistsError:
        if not payload.exist_ok:
            raise HTTPException(status_code=409, detail="Diretório já existe.")
    except Exception as e:
        logger.error("[fs] mkdir falhou em %s: %s", target, e)
        raise HTTPException(status_code=500, detail="falha ao criar diretório")

    _apply_chmod(target, payload.chmod)
    logger.info("[fs] mkdir path=%s parents=%s exist_ok=%s", target, payload.parents, payload.exist_ok)
    return {"path": str(target.relative_to(BASE)), "created": True, "chmod_applied": payload.chmod is not None}


@router.delete("/delete")
def fs_delete(payload: DeleteRequest):
    """
    Remove um arquivo ou diretório sob APP_ROOT.

    Regras:
    - Se `recursive=False` e `path` for diretório não-vazio → 400.
    - Se `recursive=True` e `path` for diretório → remove recursivamente.
    - Se `missing_ok=True` e o caminho não existir → 200 com `removed=False`.

    ⚠️ Use com cuidado; não há lixeira.
    """
    target = _safe_join(payload.path)

    if not target.exists():
        if payload.missing_ok:
            logger.info("[fs] delete path=%s (já inexistente)", target)
            return {"path": str(target), "removed": False, "reason": "missing"}
        raise HTTPException(status_code=404, detail="Caminho não encontrado.")

    # Arquivo simples
    if target.is_file() or target.is_symlink():
        try:
            target.unlink()
            logger.info("[fs] delete file path=%s ok", target)
            return {"path": str(target.relative_to(BASE)), "removed": True, "type": "file"}
        except Exception as e:
            logger.error("[fs] delete file falhou (%s): %s", target, e)
            raise HTTPException(status_code=500, detail="falha ao remover arquivo")

    # Diretório
    if target.is_dir():
        if payload.recursive:
            try:
                shutil.rmtree(target)
                logger.info("[fs] delete dir (recursive) path=%s ok", target)
                return {"path": str(target.relative_to(BASE)), "removed": True, "type": "dir", "recursive": True}
            except Exception as e:
                logger.error("[fs] delete dir recursive falhou (%s): %s", target, e)
                raise HTTPException(status_code=500, detail="falha ao remover diretório (recursivo)")
        else:
            try:
                target.rmdir()
                logger.info("[fs] delete dir (empty) path=%s ok", target)
                return {"path": str(target.relative_to(BASE)), "removed": True, "type": "dir", "recursive": False}
            except OSError:
                raise HTTPException(status_code=400, detail="diretório não está vazio (use recursive=True)")
            except Exception as e:
                logger.error("[fs] delete dir falhou (%s): %s", target, e)
                raise HTTPException(status_code=500, detail="falha ao remover diretório")

    raise HTTPException(status_code=400, detail="tipo de caminho não suportado para remoção")


@router.post("/move")
def fs_move(payload: MoveRequest):
    """
    Move ou renomeia um arquivo/diretório dentro do APP_ROOT.

    Regras:
    - Ambos os caminhos são validados e confinados ao APP_ROOT.
    - Se `overwrite=False` e o destino existe → 409 Conflict.
    - Se `overwrite=True`, remove destino existente (arquivo: unlink; diretório: rmtree).
    - Se `make_dirs=True`, cria diretórios pais do destino.

    Retorna metadados da operação.
    """
    src = _safe_join(payload.src)
    dst = _safe_join(payload.dst)

    if not src.exists():
        raise HTTPException(status_code=404, detail="Origem não encontrada.")

    # Evita mover diretório para dentro de si mesmo
    try:
        if src.is_dir() and str(dst).startswith(str(src) + os.sep):
            raise HTTPException(status_code=400, detail="Destino não pode estar dentro da própria origem.")
    except Exception:
        pass

    # Cria diretórios pais do destino, se necessário
    if payload.make_dirs:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("[fs] move: falha ao criar pais de %s: %s", dst, e)
            raise HTTPException(status_code=500, detail="falha ao criar diretórios pais do destino")

    # Lida com destino existente
    if dst.exists():
        if not payload.overwrite:
            raise HTTPException(status_code=409, detail="Destino já existe (use overwrite=True).")
        try:
            if dst.is_file() or dst.is_symlink():
                dst.unlink()
            elif dst.is_dir():
                shutil.rmtree(dst)
        except Exception as e:
            logger.error("[fs] move: falha ao remover destino existente %s: %s", dst, e)
            raise HTTPException(status_code=500, detail="falha ao remover destino existente")

    try:
        shutil.move(str(src), str(dst))
    except Exception as e:
        logger.error("[fs] move: erro ao mover %s -> %s: %s", src, dst, e)
        raise HTTPException(status_code=500, detail="erro ao mover/renomear")

    logger.info("[fs] move src=%s dst=%s overwrite=%s", src, dst, payload.overwrite)
    return {
        "src": str(src.relative_to(BASE)),
        "dst": str(dst.relative_to(BASE)),
        "is_dir": dst.is_dir(),
        "is_file": dst.is_file(),
        "overwrote": payload.overwrite,
    }


@router.post("/copy")
def fs_copy(payload: CopyRequest):
    """
    Copia um arquivo ou diretório dentro do APP_ROOT.

    Regras:
    - Se `overwrite=False` e o destino existe → 409 Conflict.
    - Se `overwrite=True`, remove destino existente antes de copiar.
    - Diretórios são copiados recursivamente (`copytree`).
    - Arquivos usam `copy2` (preserva metadata) se `preserve_times=True`, senão `copy`.

    Retorna metadados da operação.
    """
    src = _safe_join(payload.src)
    dst = _safe_join(payload.dst)

    if not src.exists():
        raise HTTPException(status_code=404, detail="Origem não encontrada.")

    # Cria diretórios pais do destino, se necessário
    if payload.make_dirs:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("[fs] copy: falha ao criar pais de %s: %s", dst, e)
            raise HTTPException(status_code=500, detail="falha ao criar diretórios pais do destino")

    if dst.exists():
        if not payload.overwrite:
            raise HTTPException(status_code=409, detail="Destino já existe (use overwrite=True).")
        try:
            if dst.is_file() or dst.is_symlink():
                dst.unlink()
            elif dst.is_dir():
                shutil.rmtree(dst)
        except Exception as e:
            logger.error("[fs] copy: falha ao remover destino existente %s: %s", dst, e)
            raise HTTPException(status_code=500, detail="falha ao remover destino existente")

    try:
        if src.is_dir():
            # copytree exige que o destino não exista
            shutil.copytree(src, dst, copy_function=shutil.copy2 if payload.preserve_times else shutil.copy)
        else:
            if payload.preserve_times:
                shutil.copy2(src, dst)
            else:
                shutil.copy(src, dst)
    except Exception as e:
        logger.error("[fs] copy: erro ao copiar %s -> %s: %s", src, dst, e)
        raise HTTPException(status_code=500, detail="erro ao copiar")

    logger.info("[fs] copy src=%s dst=%s overwrite=%s preserve_times=%s", src, dst, payload.overwrite, payload.preserve_times)
    return {
        "src": str(src.relative_to(BASE)),
        "dst": str(dst.relative_to(BASE)),
        "is_dir": dst.is_dir(),
        "is_file": dst.is_file(),
        "overwrote": payload.overwrite,
        "preserve_times": payload.preserve_times,
    }


@router.post("/touch")
def fs_touch(payload: TouchRequest):
    """
    Cria um arquivo vazio ou atualiza seu mtime (sem alterar conteúdo).

    Comportamento:
    - `make_dirs=True` cria diretórios pais.
    - `exist_ok=True` atualiza mtime se já existir; caso False e existir, retorna 409.
    """
    target = _safe_join(payload.path)

    if payload.make_dirs:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("[fs] touch: falha ao criar pais de %s: %s", target, e)
            raise HTTPException(status_code=500, detail="falha ao criar diretórios pais")

    if target.exists() and not payload.exist_ok:
        raise HTTPException(status_code=409, detail="Arquivo já existe (use exist_ok=True).")

    try:
        # touch: cria se não existir, atualiza mtime se existir
        target.touch(exist_ok=True)
    except Exception as e:
        logger.error("[fs] touch: erro em %s: %s", target, e)
        raise HTTPException(status_code=500, detail="falha no touch")

    _apply_chmod(target, payload.chmod)
    logger.info("[fs] touch path=%s", target)
    return {"path": str(target.relative_to(BASE)), "touched": True, "chmod_applied": payload.chmod is not None}


@router.get("/download")
def fs_download(
    path: str = Query(..., description="Caminho RELATIVO do arquivo"),
    filename: str | None = Query(None, description="Nome sugerido no download (opcional)"),
    as_attachment: bool = Query(True, description="Se True, força download (attachment); se False, inline"),
):
    """
    Faz o download de um arquivo como attachment (stream seguro).

    Query:
        path: caminho RELATIVO do arquivo em APP_ROOT.
        filename: nome opcional do arquivo para o cabeçalho de download.
        as_attachment: True para forçar download; False para exibir inline (se o browser suportar).

    Segurança:
    - Caminho é validado por `_safe_join`.
    - Apenas arquivos são permitidos (não diretórios).
    """
    target = _safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Caminho não é arquivo.")

    # MIME guess
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"

    download_name = filename or target.name

    logger.info("[fs] download path=%s as_attachment=%s name=%s", target, as_attachment, download_name)
    # FileResponse já define Content-Disposition quando `filename` é fornecido (attachment).
    # Para inline, não passamos filename; browsers podem tentar abrir em aba.
    return FileResponse(
        path=str(target),
        media_type=mime,
        filename=download_name if as_attachment else None,
    )