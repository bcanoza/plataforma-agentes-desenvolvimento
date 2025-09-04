# app/services/module_registry_service.py
"""
Service para gerenciar registry de módulos no banco de dados.

Responsabilidade:
- CRUD de módulos registrados
- Validação de manifesto e dependências
- Estado e health tracking
- Configuração dinâmica por módulo
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Protocol
import json

from app.core.logging_config import get_logger
from app.controllers.db_controller import get_conn

logger = get_logger("services.module_registry")


# =========================
#   DOMAIN MODELS
# =========================
@dataclass
class ModuleInfo:
    """Informações completas de um módulo."""
    id: str
    name: str
    kind: str  # system, admin, optional
    version: str
    status: str  # active, disabled, error, installing
    
    # UI
    display_order: int
    description: Optional[str]
    author: Optional[str]
    icon: Optional[str]
    
    # Configuração
    manifest: dict
    config: dict
    
    # Estado
    installed_at: str
    last_loaded_at: Optional[str]
    last_error_at: Optional[str]
    error_message: Optional[str]
    load_count: int
    
    # Auditoria
    created_at: str
    updated_at: str


@dataclass
class ModuleDependency:
    """Dependência entre módulos."""
    module_id: str
    depends_on: str
    version_min: Optional[str]
    version_max: Optional[str]
    required: bool


@dataclass
class ModuleHealth:
    """Estado de saúde de um módulo."""
    module_id: str
    check_type: str  # startup, periodic, manual
    status: str     # healthy, degraded, unhealthy
    message: Optional[str]
    response_time_ms: Optional[int]
    details: Optional[dict]
    checked_at: str


# =========================
#   REPOSITORY INTERFACE
# =========================
class ModuleRepo(Protocol):
    """Interface do repository de módulos."""
    
    async def find_all(self) -> List[ModuleInfo]:
        ...
    
    async def find_by_id(self, module_id: str) -> Optional[ModuleInfo]:
        ...
        
    async def find_by_status(self, status: str) -> List[ModuleInfo]:
        ...
        
    async def insert_module(self, **fields) -> ModuleInfo:
        ...
        
    async def update_module(self, module_id: str, **fields) -> Optional[ModuleInfo]:
        ...
        
    async def delete_module(self, module_id: str) -> bool:
        ...
        
    # Dependências
    async def get_dependencies(self, module_id: str) -> List[ModuleDependency]:
        ...
        
    async def add_dependency(self, module_id: str, depends_on: str, **opts) -> bool:
        ...
        
    # Health
    async def record_health_check(self, module_id: str, health: ModuleHealth) -> None:
        ...


# =========================
#   CUSTOM EXCEPTIONS
# =========================
class ModuleError(Exception):
    """Exception específica do registry de módulos."""
    
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message  
        self.details = details
        super().__init__(f"{code}: {message}")


# =========================
#   MODULE REGISTRY SERVICE
# =========================
class ModuleRegistryService:
    """Service principal para gerenciar registry de módulos."""
    
    def __init__(self, module_repo: ModuleRepo):
        self.repo = module_repo
    
    # ---------- READ ----------
    async def list_modules(self, *, status: Optional[str] = None) -> List[ModuleInfo]:
        """Lista módulos, opcionalmente filtrados por status."""
        logger.info("list_modules.start", extra={"status": status})
        
        if status:
            modules = await self.repo.find_by_status(status)
        else:
            modules = await self.repo.find_all()
            
        # Ordenar por display_order
        modules.sort(key=lambda m: m.display_order)
        
        logger.info("list_modules.ok", extra={"count": len(modules), "status": status})
        return modules
    
    async def get_module(self, module_id: str) -> Optional[ModuleInfo]:
        """Obtém informações de um módulo específico."""
        logger.info("get_module.start", extra={"module_id": module_id})
        
        module = await self.repo.find_by_id(module_id)
        
        if module:
            logger.info("get_module.ok", extra={"module_id": module_id})
        else:
            logger.info("get_module.not_found", extra={"module_id": module_id})
            
        return module
    
    async def get_active_modules(self) -> List[ModuleInfo]:
        """Retorna apenas módulos ativos, ordenados por dependência."""
        modules = await self.repo.find_by_status("active")
        
        # TODO: Implementar ordenação topológica por dependências
        # Por enquanto, ordenar por display_order
        modules.sort(key=lambda m: m.display_order)
        
        return modules
    
    # ---------- REGISTRATION ----------
    async def register_module(self, manifest: dict, config: Optional[dict] = None) -> ModuleInfo:
        """
        Registra novo módulo no sistema.
        
        Args:
            manifest: Manifesto JSON do módulo
            config: Configuração inicial (opcional)
            
        Returns:
            ModuleInfo do módulo registrado
        """
        module_id = manifest.get("id")
        if not module_id:
            raise ModuleError("ERR_INVALID_MANIFEST", "Manifesto deve ter campo 'id'")
        
        logger.info("register_module.start", extra={"module_id": module_id})
        
        # Validar manifesto
        self._validate_manifest(manifest)
        
        # Verificar se já existe
        existing = await self.repo.find_by_id(module_id)
        if existing:
            raise ModuleError("ERR_MODULE_EXISTS", f"Módulo '{module_id}' já registrado")
        
        # Verificar dependências
        await self._validate_dependencies(manifest.get("dependencies", []))
        
        # Registrar módulo
        now = datetime.now(timezone.utc).isoformat()
        module = await self.repo.insert_module(
            id=module_id,
            name=manifest["name"],
            kind=manifest["kind"],
            version=manifest["version"],
            status="registered",  # inicial
            display_order=manifest.get("order", 1000),
            description=manifest.get("description"),
            author=manifest.get("author"),
            icon=manifest.get("icon"),
            manifest=manifest,
            config=config or {},
            installed_at=now,
            created_at=now,
            updated_at=now,
        )
        
        # Registrar dependências
        for dep in manifest.get("dependencies", []):
            await self.repo.add_dependency(
                module_id=module_id,
                depends_on=dep["module"],
                version_min=dep.get("version_min"),
                version_max=dep.get("version_max"),
                required=dep.get("required", True)
            )
        
        logger.info("register_module.ok", extra={"module_id": module_id})
        return module
    
    # ---------- CONFIGURATION ----------
    async def update_config(self, module_id: str, config: dict) -> bool:
        """Atualiza configuração de um módulo."""
        logger.info("update_config.start", extra={"module_id": module_id})
        
        module = await self.repo.update_module(
            module_id,
            config=config,
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        if module:
            logger.info("update_config.ok", extra={"module_id": module_id})
            return True
        else:
            logger.info("update_config.not_found", extra={"module_id": module_id})
            return False
    
    async def get_config(self, module_id: str) -> Optional[dict]:
        """Obtém configuração de um módulo."""
        module = await self.repo.find_by_id(module_id)
        return module.config if module else None
    
    # ---------- STATUS MANAGEMENT ----------
    async def set_module_status(self, module_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """Atualiza status de um módulo."""
        logger.info("set_status.start", extra={"module_id": module_id, "status": status})
        
        update_fields = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if status == "error":
            update_fields["error_message"] = error_message
            update_fields["last_error_at"] = datetime.now(timezone.utc).isoformat()
        elif status == "active":
            update_fields["last_loaded_at"] = datetime.now(timezone.utc).isoformat()
            update_fields["error_message"] = None  # Limpar erro anterior
        
        module = await self.repo.update_module(module_id, **update_fields)
        
        if module:
            logger.info("set_status.ok", extra={"module_id": module_id, "status": status})
            return True
        else:
            logger.info("set_status.not_found", extra={"module_id": module_id})
            return False
    
    async def increment_load_count(self, module_id: str) -> bool:
        """Incrementa contador de carregamentos."""
        module = await self.repo.find_by_id(module_id)
        if not module:
            return False
            
        return await self.repo.update_module(
            module_id,
            load_count=module.load_count + 1,
            last_loaded_at=datetime.now(timezone.utc).isoformat()
        ) is not None
    
    # ---------- HEALTH TRACKING ----------
    async def record_health_check(
        self, 
        module_id: str, 
        check_type: str,
        status: str,
        message: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        details: Optional[dict] = None
    ) -> None:
        """Registra resultado de health check."""
        health = ModuleHealth(
            module_id=module_id,
            check_type=check_type,
            status=status,
            message=message,
            response_time_ms=response_time_ms,
            details=details,
            checked_at=datetime.now(timezone.utc).isoformat()
        )
        
        await self.repo.record_health_check(module_id, health)
        
        logger.info("health_check.recorded", extra={
            "module_id": module_id,
            "status": status, 
            "check_type": check_type
        })
    
    # ---------- DEPENDENCIES ----------
    async def get_dependencies(self, module_id: str) -> List[ModuleDependency]:
        """Retorna dependências de um módulo."""
        return await self.repo.get_dependencies(module_id)
    
    async def validate_dependency_chain(self, module_id: str) -> bool:
        """Valida se todas as dependências estão ativas."""
        dependencies = await self.get_dependencies(module_id)
        
        for dep in dependencies:
            if dep.required:
                dep_module = await self.repo.find_by_id(dep.depends_on)
                if not dep_module or dep_module.status != "active":
                    raise ModuleError(
                        "ERR_DEPENDENCY_NOT_ACTIVE",
                        f"Dependência '{dep.depends_on}' não está ativa"
                    )
        
        return True
    
    # ---------- VALIDATION ----------
    def _validate_manifest(self, manifest: dict) -> None:
        """Valida estrutura do manifesto."""
        required_fields = ["id", "name", "kind", "version"]
        
        for field in required_fields:
            if field not in manifest:
                raise ModuleError("ERR_INVALID_MANIFEST", f"Campo '{field}' obrigatório")
        
        # Validar kind
        if manifest["kind"] not in ["system", "admin", "optional"]:
            raise ModuleError("ERR_INVALID_KIND", "kind deve ser system, admin ou optional")
        
        # Validar buttons (se existir)
        if "buttons" in manifest:
            for button in manifest["buttons"]:
                if not all(k in button for k in ["id", "label", "route"]):
                    raise ModuleError("ERR_INVALID_BUTTON", "Botão deve ter id, label e route")
        
        # Validar APIs (se existir)
        if "apis" in manifest:
            for api in manifest["apis"]:
                if not all(k in api for k in ["id", "baseUrl", "auth"]):
                    raise ModuleError("ERR_INVALID_API", "API deve ter id, baseUrl e auth")
    
    async def _validate_dependencies(self, dependencies: List[dict]) -> None:
        """Valida se dependências existem e estão disponíveis."""
        for dep in dependencies:
            dep_module_id = dep.get("module")
            if not dep_module_id:
                raise ModuleError("ERR_INVALID_DEPENDENCY", "Dependência deve ter campo 'module'")
            
            dep_module = await self.repo.find_by_id(dep_module_id)
            if not dep_module:
                raise ModuleError(
                    "ERR_DEPENDENCY_NOT_FOUND", 
                    f"Módulo dependente '{dep_module_id}' não encontrado"
                )
            
            # TODO: Validar versão se especificada
            version_min = dep.get("version_min")
            if version_min:
                # Implementar comparação de versões
                pass


# =========================
#   REPOSITORY IMPLEMENTATION
# =========================
class PgModuleRepo:
    """Repository PostgreSQL para módulos."""
    
    async def find_all(self) -> List[ModuleInfo]:
        """Lista todos os módulos."""
        async with get_conn() as conn:
            rows = await conn.fetch("SELECT * FROM modules ORDER BY display_order, name")
            return [self._row_to_module(row) for row in rows]
    
    async def find_by_id(self, module_id: str) -> Optional[ModuleInfo]:
        """Busca módulo por ID."""
        async with get_conn() as conn:
            row = await conn.fetchrow("SELECT * FROM modules WHERE id = $1", module_id)
            return self._row_to_module(row) if row else None
    
    async def find_by_status(self, status: str) -> List[ModuleInfo]:
        """Lista módulos por status."""
        async with get_conn() as conn:
            rows = await conn.fetch(
                "SELECT * FROM modules WHERE status = $1 ORDER BY display_order, name", 
                status
            )
            return [self._row_to_module(row) for row in rows]
    
    async def insert_module(self, **fields) -> ModuleInfo:
        """Insere novo módulo."""
        # Converter dicts para JSON
        if "manifest" in fields and isinstance(fields["manifest"], dict):
            fields["manifest"] = json.dumps(fields["manifest"])
        if "config" in fields and isinstance(fields["config"], dict):
            fields["config"] = json.dumps(fields["config"])
        
        columns = ", ".join(fields.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(fields)))
        values = list(fields.values())
        
        query = f"""
            INSERT INTO modules ({columns}) 
            VALUES ({placeholders})
            RETURNING *
        """
        
        async with get_conn() as conn:
            row = await conn.fetchrow(query, *values)
            return self._row_to_module(row)
    
    async def update_module(self, module_id: str, **fields) -> Optional[ModuleInfo]:
        """Atualiza módulo existente."""
        if not fields:
            return await self.find_by_id(module_id)
        
        # Converter dicts para JSON
        if "config" in fields and isinstance(fields["config"], dict):
            fields["config"] = json.dumps(fields["config"])
        if "manifest" in fields and isinstance(fields["manifest"], dict):
            fields["manifest"] = json.dumps(fields["manifest"])
        
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields.keys()))
        values = [module_id] + list(fields.values())
        
        query = f"""
            UPDATE modules 
            SET {set_clauses}
            WHERE id = $1
            RETURNING *
        """
        
        async with get_conn() as conn:
            row = await conn.fetchrow(query, *values)
            return self._row_to_module(row) if row else None
    
    async def delete_module(self, module_id: str) -> bool:
        """Remove módulo."""
        async with get_conn() as conn:
            result = await conn.execute("DELETE FROM modules WHERE id = $1", module_id)
            return result == "DELETE 1"
    
    # ---------- DEPENDENCIES ----------
    async def get_dependencies(self, module_id: str) -> List[ModuleDependency]:
        """Retorna dependências de um módulo."""
        async with get_conn() as conn:
            rows = await conn.fetch(
                """
                SELECT module_id, depends_on, version_min, version_max, required
                FROM module_dependencies
                WHERE module_id = $1
                """,
                module_id
            )
            return [
                ModuleDependency(
                    module_id=row["module_id"],
                    depends_on=row["depends_on"],
                    version_min=row["version_min"],
                    version_max=row["version_max"],
                    required=row["required"]
                )
                for row in rows
            ]
    
    async def add_dependency(
        self, 
        module_id: str, 
        depends_on: str, 
        version_min: Optional[str] = None,
        version_max: Optional[str] = None,
        required: bool = True
    ) -> bool:
        """Adiciona dependência entre módulos."""
        try:
            async with get_conn() as conn:
                await conn.execute(
                    """
                    INSERT INTO module_dependencies (module_id, depends_on, version_min, version_max, required)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    module_id, depends_on, version_min, version_max, required
                )
                return True
        except Exception as e:
            logger.error("add_dependency.failed", extra={
                "module_id": module_id, 
                "depends_on": depends_on,
                "error": str(e)
            })
            return False
    
    # ---------- HEALTH TRACKING ---------- 
    async def record_health_check(self, module_id: str, health: ModuleHealth) -> None:
        """Registra resultado de health check."""
        details_json = json.dumps(health.details) if health.details else None
        
        async with get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO module_health_checks 
                (module_id, check_type, status, message, response_time_ms, details, checked_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                health.module_id, health.check_type, health.status, health.message,
                health.response_time_ms, details_json, health.checked_at
            )
    
    # ---------- HELPERS ----------
    def _row_to_module(self, row) -> ModuleInfo:
        """Converte row SQL para ModuleInfo."""
        # Parse JSON fields
        manifest = json.loads(row["manifest"]) if row["manifest"] else {}
        config = json.loads(row["config"]) if row["config"] else {}
        
        return ModuleInfo(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            version=row["version"],
            status=row["status"],
            display_order=row["display_order"],
            description=row["description"],
            author=row["author"],
            icon=row["icon"],
            manifest=manifest,
            config=config,
            installed_at=row["installed_at"].isoformat() if row["installed_at"] else None,
            last_loaded_at=row["last_loaded_at"].isoformat() if row["last_loaded_at"] else None,
            last_error_at=row["last_error_at"].isoformat() if row["last_error_at"] else None,
            error_message=row["error_message"],
            load_count=row["load_count"],
            created_at=row["created_at"].isoformat() if row["created_at"] else None,
            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        )