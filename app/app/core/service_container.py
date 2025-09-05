# app/core/service_container.py
"""
Container centralizado de Dependency Injection para módulos.

Este container:
- Registra services por módulo
- Resolve dependências automaticamente  
- Gerencia lifecycle (singleton, request-scoped)
- Permite hot-reload de services
- Tracking de performance e usage
"""
from __future__ import annotations

from typing import Dict, Type, Any, Optional, TypeVar, Callable, List, Set
from dataclasses import dataclass, field
import asyncio
import uuid
import time
from datetime import datetime

from app.core.logging_config import get_logger

logger = get_logger("core.service_container")

T = TypeVar('T')


@dataclass
class ServiceDefinition:
    """Definição de como criar um service."""
    name: str
    service_class: Type
    factory_func: Callable[..., Any]
    module_id: str
    
    # Configurações
    singleton: bool = True
    lifecycle: str = "application"  # application, request, module
    dependencies: List[str] = field(default_factory=list)
    
    # Estado
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    instance_count: int = 0
    last_created_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ServiceInstance:
    """Instância de service ativa."""
    service: Any
    definition: ServiceDefinition
    instance_id: str
    created_at: str
    request_count: int = 0


class ServiceContainer:
    """Container centralizado de dependency injection."""
    
    def __init__(self):
        # Registry de definições
        self._definitions: Dict[str, ServiceDefinition] = {}
        
        # Instâncias ativas (singletons)
        self._instances: Dict[str, ServiceInstance] = {}
        
        # Mapeamento módulo → services
        self._module_services: Dict[str, Set[str]] = {}
        
        # Resolução de dependências (evitar ciclos)
        self._resolving: Set[str] = set()
        
        # Metrics
        self._total_resolutions: int = 0
    
    def register(
        self, 
        name: str, 
        service_class: Type[T], 
        factory_func: Callable[..., T],
        *,
        module_id: str,
        singleton: bool = True,
        dependencies: Optional[List[str]] = None,
        lifecycle: str = "application"
    ) -> None:
        """
        Registra um service no container.
        
        Args:
            name: Nome único do service (ex: "user_service")
            service_class: Classe do service (UserService) 
            factory_func: Função para criar instância
            module_id: ID do módulo dono
            singleton: Se deve reutilizar instância
            dependencies: Lista de services necessários
            lifecycle: Ciclo de vida (application, request, module)
        """
        if name in self._definitions:
            logger.warning("service.register.overwrite", extra={"service": name, "module": module_id})
        
        definition = ServiceDefinition(
            name=name,
            service_class=service_class,
            factory_func=factory_func,
            module_id=module_id,
            singleton=singleton,
            dependencies=dependencies or [],
            lifecycle=lifecycle
        )
        
        self._definitions[name] = definition
        
        # Mapear ao módulo
        if module_id not in self._module_services:
            self._module_services[module_id] = set()
        self._module_services[module_id].add(name)
        
        logger.info("service.registered", extra={
            "service": name, 
            "module": module_id,
            "singleton": singleton,
            "dependencies": dependencies
        })
    
    async def get(self, name: str) -> Any:
        """
        Obtém instância de service, resolvendo dependências.
        
        Retorna:
            Instância do service solicitado
            
        Raises:
            ValueError: Service não registrado
            RuntimeError: Dependência circular
        """
        if name not in self._definitions:
            available = list(self._definitions.keys())
            raise ValueError(f"Service '{name}' não registrado. Disponíveis: {available}")
        
        # Evitar dependência circular
        if name in self._resolving:
            chain = " -> ".join(self._resolving) + f" -> {name}"
            raise RuntimeError(f"Dependência circular detectada: {chain}")
        
        definition = self._definitions[name]
        
        # Singleton: reutilizar instância existente
        if definition.singleton and name in self._instances:
            instance_wrapper = self._instances[name]
            instance_wrapper.request_count += 1
            return instance_wrapper.service
        
        # Resolver dependências primeiro
        self._resolving.add(name)
        try:
            resolved_deps = {}
            for dep_name in definition.dependencies:
                resolved_deps[dep_name] = await self.get(dep_name)
        finally:
            self._resolving.discard(name)
        
        # Criar nova instância
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(definition.factory_func):
                service = await definition.factory_func(**resolved_deps)
            else:
                service = definition.factory_func(**resolved_deps)
                
            # Wrapper da instância
            instance_wrapper = ServiceInstance(
                service=service,
                definition=definition,
                instance_id=str(uuid.uuid4()),
                created_at=datetime.utcnow().isoformat(),
            )
            
            # Cachear se singleton
            if definition.singleton:
                self._instances[name] = instance_wrapper
            
            # Atualizar metrics
            definition.instance_count += 1
            definition.last_created_at = instance_wrapper.created_at
            definition.error_message = None
            self._total_resolutions += 1
            
            create_time = (time.time() - start_time) * 1000
            logger.info("service.created", extra={
                "service": name,
                "module": definition.module_id, 
                "instance_id": instance_wrapper.instance_id,
                "create_time_ms": create_time,
                "singleton": definition.singleton
            })
            
            return service
            
        except Exception as e:
            definition.error_message = str(e)
            logger.error("service.create_failed", extra={
                "service": name,
                "module": definition.module_id,
                "error": str(e)
            })
            raise
    
    async def unload_module(self, module_id: str) -> int:
        """
        Remove todos os services de um módulo.
        
        Returns:
            Número de services removidos
        """
        if module_id not in self._module_services:
            return 0
        
        service_names = list(self._module_services[module_id])
        removed_count = 0
        
        for service_name in service_names:
            try:
                # Cleanup de instâncias ativas
                if service_name in self._instances:
                    instance_wrapper = self._instances[service_name]
                    
                    # Chamar cleanup se existir
                    if hasattr(instance_wrapper.service, 'cleanup'):
                        if asyncio.iscoroutinefunction(instance_wrapper.service.cleanup):
                            await instance_wrapper.service.cleanup()
                        else:
                            instance_wrapper.service.cleanup()
                    
                    del self._instances[service_name]
                
                # Remove definição
                if service_name in self._definitions:
                    del self._definitions[service_name]
                    removed_count += 1
                    
                logger.info("service.unloaded", extra={"service": service_name, "module": module_id})
                
            except Exception as e:
                logger.error("service.unload_failed", extra={
                    "service": service_name, 
                    "module": module_id,
                    "error": str(e)
                })
        
        # Limpar mapeamento do módulo
        del self._module_services[module_id]
        
        logger.info("module.services_unloaded", extra={
            "module": module_id, 
            "removed_count": removed_count
        })
        
        return removed_count
    
    def get_module_services(self, module_id: str) -> List[str]:
        """Retorna lista de services de um módulo."""
        return list(self._module_services.get(module_id, set()))
    
    def get_service_info(self, name: str) -> Optional[ServiceDefinition]:
        """Retorna definição de um service."""
        return self._definitions.get(name)
    
    def get_instance_info(self, name: str) -> Optional[ServiceInstance]:
        """Retorna informações da instância ativa."""
        return self._instances.get(name)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do container."""
        active_instances = len(self._instances)
        registered_services = len(self._definitions)
        modules_with_services = len(self._module_services)
        
        return {
            "registered_services": registered_services,
            "active_instances": active_instances, 
            "modules_with_services": modules_with_services,
            "total_resolutions": self._total_resolutions,
            "modules": {
                module_id: len(services) 
                for module_id, services in self._module_services.items()
            }
        }
    
    async def health_check(self) -> dict:
        """Verifica saúde de todos os services."""
        results = {}
        
        for name, instance_wrapper in self._instances.items():
            try:
                # Health check específico do service
                if hasattr(instance_wrapper.service, 'health_check'):
                    start_time = time.time()
                    if asyncio.iscoroutinefunction(instance_wrapper.service.health_check):
                        health = await instance_wrapper.service.health_check()
                    else:
                        health = instance_wrapper.service.health_check()
                    response_time = (time.time() - start_time) * 1000
                    
                    results[name] = {
                        "status": "healthy" if health.get("ok", True) else "unhealthy",
                        "details": health,
                        "response_time_ms": response_time,
                        "instance_id": instance_wrapper.instance_id,
                        "request_count": instance_wrapper.request_count
                    }
                else:
                    # Service sem health check - assumir saudável se instância existe
                    results[name] = {
                        "status": "healthy",
                        "details": {"message": "No health check available"},
                        "instance_id": instance_wrapper.instance_id,
                        "request_count": instance_wrapper.request_count
                    }
                    
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "instance_id": instance_wrapper.instance_id if instance_wrapper else None
                }
        
        return results


# Container global - instância única por aplicação
container = ServiceContainer()