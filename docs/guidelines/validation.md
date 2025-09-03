# Diretrizes de Validação de Contratos

## Visão Geral

Esta documentação estabelece diretrizes **obrigatórias** para validação de contratos entre módulos e agentes na Plataforma de Agentes de Desenvolvimento. O sistema de validação garante que todas as comunicações sigam os contratos definidos.

## 1. Sistema de Validação

### 1.1 Componentes

O sistema de validação consiste em:

- **ContractValidator**: Interface para validadores específicos
- **ContractValidationRegistry**: Registry central de validadores
- **ValidationResult**: Resultado estruturado da validação
- **Decorators**: Validação automática via decorators

### 1.2 Localização

```python
# Validador principal
app/core/contract_validator.py

# Validadores específicos por módulo
app/api/auth/validators.py
app/api/agents/validators.py
app/api/workspace/validators.py
```

## 2. Uso do Sistema

### 2.1 Validação Manual

```python
from app.core.contract_validator import validate_contract_call

# Validar requisição
try:
    result = validate_contract_call(
        contract_name="auth-workspace",
        data={
            "user_id": "123",
            "workspace_id": "456",
            "operation": "read"
        },
        request_type="request"
    )
    print(f"Validação bem-sucedida: {result.is_valid}")
except ContractViolationError as e:
    print(f"Erro de contrato: {e}")
```

### 2.2 Validação com Decorator

```python
from app.core.contract_validator import validate_contract

@validate_contract("auth-workspace", "request")
async def validate_workspace_access(
    user_id: str,
    workspace_id: str,
    operation: str
) -> bool:
    """Valida acesso ao workspace."""
    # Implementação da validação
    pass
```

### 2.3 Validação de Eventos

```python
from app.core.contract_validator import validate_event_data

# Validar evento
result = validate_event_data("code_generated", {
    "session_id": "123",
    "agent_id": "generator_001",
    "code": "def hello(): pass",
    "language": "python",
    "timestamp": datetime.utcnow()
})
```

## 3. Criação de Validadores

### 3.1 Validador Básico

```python
from app.core.contract_validator import BaseContractValidator

class MeuContratoValidator(BaseContractValidator):
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["campo1", "campo2"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        result = super().validate_request(data)
        
        # Validações específicas
        if "campo1" in data and not isinstance(data["campo1"], str):
            result.errors.append("campo1 deve ser string")
        
        result.is_valid = len(result.errors) == 0
        return result
```

### 3.2 Validador Avançado

```python
class ContratoAvancadoValidator(BaseContractValidator):
    def __init__(self):
        super().__init__(
            contract_version="1.0.0",
            required_fields=["id", "data"]
        )
    
    def validate_request(self, data: Dict[str, Any]) -> ValidationResult:
        result = super().validate_request(data)
        
        # Validação de formato
        if "id" in data:
            if not self._validate_id_format(data["id"]):
                result.errors.append("ID deve ter formato UUID")
        
        # Validação de negócio
        if "data" in data:
            if not self._validate_business_rules(data["data"]):
                result.errors.append("Dados violam regras de negócio")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_id_format(self, id_value: str) -> bool:
        """Valida formato do ID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, id_value))
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Valida regras de negócio."""
        # Implementar validações específicas
        return True
```

## 4. Registro de Validadores

### 4.1 Registro Automático

```python
# No __init__.py do módulo
from app.core.contract_validator import contract_registry
from .validators import MeuContratoValidator

# Registrar validador
contract_registry.register("meu-contrato", MeuContratoValidator())
```

### 4.2 Registro Manual

```python
from app.core.contract_validator import contract_registry

# Registrar validador personalizado
validator = MeuContratoValidator()
contract_registry.register("contrato-personalizado", validator)
```

## 5. Tratamento de Erros

### 5.1 Tipos de Erro

```python
from app.core.contract_validator import (
    ValidationError,
    ContractViolationError
)

try:
    validate_contract_call("meu-contrato", data)
except ContractViolationError as e:
    # Erro de violação de contrato
    logger.error(f"Contrato violado: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except ValidationError as e:
    # Erro de validação
    logger.error(f"Erro de validação: {e}")
    raise HTTPException(status_code=422, detail=str(e))
```

### 5.2 Resposta de Erro Estruturada

```python
@router.post("/endpoint")
async def meu_endpoint(request: RequestData):
    try:
        validate_contract_call("meu-contrato", request.dict())
        # Processar requisição
        return {"status": "success"}
    except ContractViolationError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "CONTRACT_VIOLATION",
                "message": str(e),
                "contract": "meu-contrato",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## 6. Monitoramento e Logging

### 6.1 Logging de Validação

```python
import logging

logger = logging.getLogger(__name__)

# Log de validação bem-sucedida
logger.info(f"Contrato validado: {contract_name}")

# Log de violação
logger.error(f"Violation of contract '{contract_name}': {errors}")

# Log de warnings
logger.warning(f"Warnings for contract '{contract_name}': {warnings}")
```

### 6.2 Métricas de Validação

```python
from prometheus_client import Counter, Histogram

# Métricas
validation_requests = Counter('contract_validation_requests_total', 
                            'Total validation requests', ['contract', 'status'])
validation_duration = Histogram('contract_validation_duration_seconds',
                              'Validation duration', ['contract'])

# Uso
with validation_duration.labels(contract=contract_name).time():
    result = validate_contract_call(contract_name, data)

validation_requests.labels(
    contract=contract_name, 
    status="success" if result.is_valid else "failure"
).inc()
```

## 7. Testes de Validação

### 7.1 Testes Unitários

```python
import pytest
from app.core.contract_validator import validate_contract_call, ContractViolationError

class TestContractValidation:
    def test_valid_request(self):
        """Testa requisição válida."""
        data = {
            "user_id": "123",
            "workspace_id": "456",
            "operation": "read"
        }
        
        result = validate_contract_call("auth-workspace", data)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_invalid_request(self):
        """Testa requisição inválida."""
        data = {
            "user_id": "123",
            # Missing workspace_id and operation
        }
        
        with pytest.raises(ContractViolationError):
            validate_contract_call("auth-workspace", data)
    
    def test_invalid_operation(self):
        """Testa operação inválida."""
        data = {
            "user_id": "123",
            "workspace_id": "456",
            "operation": "invalid_operation"
        }
        
        with pytest.raises(ContractViolationError):
            validate_contract_call("auth-workspace", data)
```

### 7.2 Testes de Integração

```python
class TestContractIntegration:
    async def test_endpoint_validation(self, client):
        """Testa validação em endpoint real."""
        # Teste com dados válidos
        response = await client.post("/workspace/validate", json={
            "user_id": "123",
            "workspace_id": "456",
            "operation": "read"
        })
        assert response.status_code == 200
        
        # Teste com dados inválidos
        response = await client.post("/workspace/validate", json={
            "user_id": "123"
            # Missing required fields
        })
        assert response.status_code == 400
        assert "CONTRACT_VIOLATION" in response.json()["error"]
```

## 8. Versionamento de Contratos

### 8.1 Compatibilidade

```python
from app.core.contract_validator import check_contract_compatibility

# Verificar compatibilidade
is_compatible = check_contract_compatibility("1.0.0", "1.1.0")
assert is_compatible is True  # Mesma versão major

is_compatible = check_contract_compatibility("1.0.0", "2.0.0")
assert is_compatible is False  # Versões major diferentes
```

### 8.2 Migração de Versão

```python
class ContractVersionMigrator:
    def migrate_to_version(self, data: Dict[str, Any], 
                          from_version: str, to_version: str) -> Dict[str, Any]:
        """Migra dados entre versões de contrato."""
        if from_version == "1.0.0" and to_version == "1.1.0":
            # Adicionar novos campos opcionais
            if "new_field" not in data:
                data["new_field"] = "default_value"
        
        return data
```

## 9. Performance e Cache

### 9.1 Cache de Validação

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_validation(contract_name: str, data_hash: str) -> ValidationResult:
    """Cache de validação para dados idênticos."""
    # Implementar validação cached
    pass

def validate_with_cache(contract_name: str, data: Dict[str, Any]) -> ValidationResult:
    """Validação com cache."""
    data_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return cached_validation(contract_name, data_hash)
```

### 9.2 Otimização

```python
# Validação assíncrona para operações pesadas
async def validate_async(contract_name: str, data: Dict[str, Any]) -> ValidationResult:
    """Validação assíncrona."""
    # Executar validação em thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        validate_contract_call, 
        contract_name, 
        data
    )
```

## 10. Compliance e Auditoria

### 10.1 Checklist de Validação

Antes de qualquer deploy:

- [ ] Validadores implementados para todos os contratos
- [ ] Testes de validação criados
- [ ] Logging configurado
- [ ] Métricas implementadas
- [ ] Documentação atualizada

### 10.2 Auditoria

```python
class ContractAuditor:
    def audit_contract_usage(self, contract_name: str, 
                           time_period: str) -> Dict[str, Any]:
        """Audita uso de contrato."""
        return {
            "contract": contract_name,
            "period": time_period,
            "total_requests": 1000,
            "validation_failures": 5,
            "failure_rate": 0.005,
            "most_common_errors": ["missing_field", "invalid_type"]
        }
```

## 11. Exemplos Práticos

### 11.1 Validação em Endpoint

```python
from fastapi import APIRouter, HTTPException
from app.core.contract_validator import validate_contract_call, ContractViolationError

router = APIRouter()

@router.post("/workspace/access")
async def validate_workspace_access(request: WorkspaceAccessRequest):
    try:
        # Validar contrato
        validate_contract_call("auth-workspace", request.dict())
        
        # Processar requisição
        has_access = await check_workspace_access(
            request.user_id,
            request.workspace_id,
            request.operation
        )
        
        return {"has_access": has_access}
        
    except ContractViolationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 11.2 Validação em Evento

```python
from app.core.contract_validator import validate_event_data

async def handle_code_generated(event: CodeGeneratedEvent):
    # Validar evento
    result = validate_event_data("code_generated", event.__dict__)
    
    if not result.is_valid:
        logger.error(f"Evento inválido: {result.errors}")
        return
    
    # Processar evento
    await process_code_generation(event)
```

---

**Importante**: O sistema de validação é **obrigatório** e deve ser usado em todas as comunicações entre módulos e agentes. Violações resultam em falha de sistema.


