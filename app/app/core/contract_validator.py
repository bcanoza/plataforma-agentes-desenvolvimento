# app/core/contract_validator.py

"""
Sistema de validação de contratos entre módulos e agentes.

Este módulo implementa validação automática de contratos para garantir
que a comunicação entre componentes siga os contratos definidos.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Protocol, Type, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Erro de validação de contrato."""
    pass


class ContractViolationError(Exception):
    """Erro de violação de contrato."""
    pass


@dataclass
class ValidationResult:
    """Resultado de validação de contrato."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    contract_version: str
    validated_at: datetime


class ContractValidator(Protocol):
    """Protocolo para validadores de contrato."""
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida dados de requisição."""
        ...
    
    def validate_response(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida dados de resposta."""
        ...


class BaseContractValidator:
    """Validador base para contratos."""
    
    def __init__(self, contract_version: str, required_fields: List[str]):
        self.contract_version = contract_version
        self.required_fields = required_fields
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida dados de requisição."""
        errors = []
        warnings = []
        
        # Validar campos obrigatórios
        for field in self.required_fields:
            if field not in data:
                errors.append(f"Campo obrigatório '{field}' não encontrado")
        
        # Validar tipos básicos
        for field, value in data.items():
            if not self._validate_field_type(field, value):
                warnings.append(f"Tipo inesperado para campo '{field}'")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            contract_version=self.contract_version,
            validated_at=datetime.utcnow()
        )
    
    def validate_response(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida dados de resposta."""
        return self.validate_request(data)  # Mesma validação por enquanto
    
    def _validate_field_type(self, field: str, value: Any) -> bool:
        """Valida tipo de campo específico."""
        # Implementação básica - pode ser estendida
        return True


class AuthWorkspaceContractValidator(BaseContractValidator):
    """Validador para contrato Auth ↔ Workspace."""
    
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["user_id", "workspace_id", "operation"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida requisição do contrato Auth-Workspace."""
        result = super().validate_request(data)
        
        # Validações específicas
        if "operation" in data:
            valid_operations = ["read", "write", "delete", "execute", "admin"]
            if data["operation"] not in valid_operations:
                result.errors.append(f"Operação inválida: {data['operation']}")
        
        if "user_id" in data and not isinstance(data["user_id"], str):
            result.errors.append("user_id deve ser string")
        
        if "workspace_id" in data and not isinstance(data["workspace_id"], str):
            result.errors.append("workspace_id deve ser string")
        
        result.is_valid = len(result.errors) == 0
        return result


class AgentsAIContractValidator(BaseContractValidator):
    """Validador para contrato Agents ↔ AI."""
    
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["prompt", "model"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida requisição do contrato Agents-AI."""
        result = super().validate_request(data)
        
        # Validações específicas
        if "prompt" in data and not isinstance(data["prompt"], str):
            result.errors.append("prompt deve ser string")
        
        if "model" in data:
            valid_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
            if data["model"] not in valid_models:
                result.warnings.append(f"Modelo não reconhecido: {data['model']}")
        
        if "temperature" in data:
            temp = data["temperature"]
            if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 1.0):
                result.errors.append("temperature deve ser float entre 0.0 e 1.0")
        
        if "max_tokens" in data:
            tokens = data["max_tokens"]
            if not isinstance(tokens, int) or tokens <= 0:
                result.errors.append("max_tokens deve ser inteiro positivo")
        
        result.is_valid = len(result.errors) == 0
        return result


class GeneratorReviewerContractValidator(BaseContractValidator):
    """Validador para contrato Generator ↔ Reviewer."""
    
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["session_id", "agent_id", "code", "language", "timestamp"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida evento do contrato Generator-Reviewer."""
        result = super().validate_request(data)
        
        # Validações específicas
        if "language" in data:
            valid_languages = ["python", "javascript", "typescript", "java", "go", "rust"]
            if data["language"] not in valid_languages:
                result.warnings.append(f"Linguagem não reconhecida: {data['language']}")
        
        if "priority" in data:
            valid_priorities = ["low", "normal", "high", "urgent"]
            if data["priority"] not in valid_priorities:
                result.errors.append(f"Prioridade inválida: {data['priority']}")
        
        if "timestamp" in data:
            if not isinstance(data["timestamp"], (str, datetime)):
                result.errors.append("timestamp deve ser string ou datetime")
        
        result.is_valid = len(result.errors) == 0
        return result


class ReviewerTesterContractValidator(BaseContractValidator):
    """Validador para contrato Reviewer ↔ Tester."""
    
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["session_id", "reviewer_id", "code", "language", "test_requirements", "timestamp"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Valida evento do contrato Reviewer-Tester."""
        result = super().validate_request(data)
        
        # Validações específicas
        if "test_requirements" in data:
            if not isinstance(data["test_requirements"], list):
                result.errors.append("test_requirements deve ser lista")
            else:
                for i, req in enumerate(data["test_requirements"]):
                    if not isinstance(req, dict):
                        result.errors.append(f"test_requirements[{i}] deve ser dicionário")
                    elif "type" not in req:
                        result.errors.append(f"test_requirements[{i}] deve ter campo 'type'")
        
        if "timeout_seconds" in data:
            timeout = data["timeout_seconds"]
            if not isinstance(timeout, int) or timeout <= 0:
                result.errors.append("timeout_seconds deve ser inteiro positivo")
        
        result.is_valid = len(result.errors) == 0
        return result


class ContractValidationRegistry:
    """Registry para validadores de contrato."""
    
    def __init__(self):
        self._validators: Dict[str, ContractValidator] = {}
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Registra validadores padrão."""
        self.register("auth-workspace", AuthWorkspaceContractValidator())
        self.register("agents-ai", AgentsAIContractValidator())
        self.register("generator-reviewer", GeneratorReviewerContractValidator())
        self.register("reviewer-tester", ReviewerTesterContractValidator())
    
    def register(self, contract_name: str, validator: ContractValidator):
        """Registra um validador de contrato."""
        self._validators[contract_name] = validator
        logger.info(f"Validador registrado para contrato: {contract_name}")
    
    def get_validator(self, contract_name: str) -> Optional[ContractValidator]:
        """Retorna validador para contrato específico."""
        return self._validators.get(contract_name)
    
    def validate_contract(self, contract_name: str, data: Dict[str, Any], 
                         request_type: str = "request") -> ValidationResult:
        """Valida dados contra contrato específico."""
        validator = self.get_validator(contract_name)
        if not validator:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validador não encontrado para contrato: {contract_name}"],
                warnings=[],
                contract_version="unknown",
                validated_at=datetime.utcnow()
            )
        
        if request_type == "request":
            return validator.validate_request(data)
        elif request_type == "response":
            return validator.validate_response(data)
        else:
            return ValidationResult(
                is_valid=False,
                errors=[f"Tipo de validação inválido: {request_type}"],
                warnings=[],
                contract_version=validator.contract_version,
                validated_at=datetime.utcnow()
            )


# Instância global do registry
contract_registry = ContractValidationRegistry()


def validate_contract_call(contract_name: str, data: Dict[str, Any], 
                          request_type: str = "request") -> ValidationResult:
    """
    Valida chamada de contrato.
    
    Args:
        contract_name: Nome do contrato
        data: Dados a serem validados
        request_type: Tipo da validação ("request" ou "response")
        
    Returns:
        ValidationResult: Resultado da validação
        
    Raises:
        ContractViolationError: Se contrato é violado
    """
    result = contract_registry.validate_contract(contract_name, data, request_type)
    
    if not result.is_valid:
        error_msg = f"Violation of contract '{contract_name}': {', '.join(result.errors)}"
        logger.error(error_msg)
        raise ContractViolationError(error_msg)
    
    if result.warnings:
        warning_msg = f"Warnings for contract '{contract_name}': {', '.join(result.warnings)}"
        logger.warning(warning_msg)
    
    return result


def validate_event_data(event_type: str, data: Dict[str, Any]) -> ValidationResult:
    """
    Valida dados de evento.
    
    Args:
        event_type: Tipo do evento
        data: Dados do evento
        
    Returns:
        ValidationResult: Resultado da validação
    """
    # Mapear tipos de evento para contratos
    event_to_contract = {
        "code_generated": "generator-reviewer",
        "code_reviewed": "generator-reviewer",
        "code_approved_for_testing": "reviewer-tester",
        "tests_completed": "reviewer-tester",
        "ai_request": "agents-ai",
        "ai_response": "agents-ai",
        "workspace_access": "auth-workspace"
    }
    
    contract_name = event_to_contract.get(event_type)
    if not contract_name:
        return ValidationResult(
            is_valid=False,
            errors=[f"Tipo de evento não reconhecido: {event_type}"],
            warnings=[],
            contract_version="unknown",
            validated_at=datetime.utcnow()
        )
    
    return validate_contract_call(contract_name, data)


# Decorator para validação automática
def validate_contract(contract_name: str, request_type: str = "request"):
    """
    Decorator para validação automática de contrato.
    
    Args:
        contract_name: Nome do contrato
        request_type: Tipo da validação
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extrair dados do primeiro argumento (assumindo que é um dict ou objeto com asdict)
            if args and hasattr(args[0], '__dict__'):
                data = asdict(args[0]) if hasattr(args[0], '__dataclass_fields__') else args[0].__dict__
            elif args and isinstance(args[0], dict):
                data = args[0]
            else:
                data = kwargs
            
            # Validar contrato
            validate_contract_call(contract_name, data, request_type)
            
            # Executar função original
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Função para gerar hash de contrato
def generate_contract_hash(contract_data: Dict[str, Any]) -> str:
    """
    Gera hash para dados de contrato.
    
    Args:
        contract_data: Dados do contrato
        
    Returns:
        str: Hash MD5 dos dados
    """
    # Ordenar dados para hash consistente
    sorted_data = json.dumps(contract_data, sort_keys=True, default=str)
    return hashlib.md5(sorted_data.encode()).hexdigest()


# Função para verificar compatibilidade de versão
def check_contract_compatibility(version1: str, version2: str) -> bool:
    """
    Verifica compatibilidade entre versões de contrato.
    
    Args:
        version1: Versão 1 (formato semver)
        version2: Versão 2 (formato semver)
        
    Returns:
        bool: True se compatíveis
    """
    def parse_version(version: str) -> tuple:
        parts = version.split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    # Compatibilidade: mesma versão major
    return v1[0] == v2[0]


# Exemplo de uso
if __name__ == "__main__":
    # Teste de validação
    test_data = {
        "user_id": "123",
        "workspace_id": "456",
        "operation": "read"
    }
    
    try:
        result = validate_contract_call("auth-workspace", test_data)
        print(f"Validação bem-sucedida: {result.is_valid}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")
    except ContractViolationError as e:
        print(f"Erro de contrato: {e}")


