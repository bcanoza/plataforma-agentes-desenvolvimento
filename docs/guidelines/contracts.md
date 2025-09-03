# Diretrizes de Contratos

## Visão Geral

Esta documentação estabelece diretrizes **obrigatórias** para criação e manutenção de contratos entre módulos e agentes na Plataforma de Agentes de Desenvolvimento.

## 1. Princípios dos Contratos

### 1.1 Definição

Um **contrato** é um acordo formal que define:
- Como módulos/agentes se comunicam
- Quais dados são trocados
- Qual o formato esperado
- Como lidar com erros
- Versionamento e compatibilidade

### 1.2 Quando Criar Contratos

**OBRIGATÓRIO** criar contrato quando:
- Um módulo chama outro módulo
- Um agente depende de outro agente
- Há troca de dados entre componentes
- Existe dependência de API externa
- Há eventos assíncronos entre componentes

### 1.3 Responsabilidades

- **Provedor**: Define e mantém o contrato
- **Consumidor**: Segue o contrato definido
- **Arquiteto**: Aprova mudanças de contrato

## 2. Estrutura de Contratos

### 2.1 Localização

Contratos devem estar em:
```
docs/contracts/
├── modules/           # Contratos entre módulos
│   ├── auth-workspace.md
│   ├── agents-ai.md
│   └── workspace-code.md
├── agents/           # Contratos entre agentes
│   ├── generator-reviewer.md
│   ├── reviewer-tester.md
│   └── tester-debugger.md
└── external/         # Contratos com APIs externas
    ├── openai-api.md
    └── github-api.md
```

### 2.2 Template Padrão

```markdown
# Contrato: [Provedor] ↔ [Consumidor]

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo
- **Responsável**: [Nome]
- **Revisado por**: [Nome]

## Visão Geral
[Descrição clara do propósito do contrato]

## Dependências
- [Lista de dependências técnicas]
- [Versões mínimas requeridas]

## Interface

### [Provedor] → [Consumidor]

#### Método/Evento: `nome_metodo`
```typescript
interface Request {
  // Estrutura da requisição
}

interface Response {
  // Estrutura da resposta
}
```

**Descrição**: [O que faz]
**Parâmetros**: [Lista de parâmetros]
**Retorno**: [O que retorna]
**Erros**: [Possíveis erros]

### [Consumidor] → [Provedor]

#### Método/Evento: `nome_metodo`
```typescript
interface Request {
  // Estrutura da requisição
}

interface Response {
  // Estrutura da resposta
}
```

**Descrição**: [O que faz]
**Parâmetros**: [Lista de parâmetros]
**Retorno**: [O que retorna]
**Erros**: [Possíveis erros]

## Fluxo de Dados
[Diagrama ou descrição do fluxo]

## Tratamento de Erros
[Como erros são tratados]

## Versionamento
[Política de versionamento]

## Exemplos
[Exemplos práticos de uso]

## Changelog
[Histórico de mudanças]
```

## 3. Contratos entre Módulos

### 3.1 Contrato Auth ↔ Workspace

```markdown
# Contrato: Auth ↔ Workspace

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo

## Visão Geral
Define como o módulo Auth valida permissões para operações no Workspace.

## Interface

### Auth → Workspace

#### Método: `validate_workspace_access`
```python
async def validate_workspace_access(
    user_id: str,
    workspace_id: str,
    operation: WorkspaceOperation
) -> bool:
    """
    Valida se usuário tem permissão para operação no workspace.
    
    Args:
        user_id: ID do usuário
        workspace_id: ID do workspace
        operation: Tipo de operação (READ, WRITE, DELETE)
        
    Returns:
        bool: True se tem permissão
        
    Raises:
        UserNotFoundError: Usuário não existe
        WorkspaceNotFoundError: Workspace não existe
    """
```

### Workspace → Auth

#### Método: `get_user_permissions`
```python
async def get_user_permissions(
    user_id: str,
    workspace_id: str
) -> List[Permission]:
    """
    Retorna permissões do usuário no workspace.
    
    Args:
        user_id: ID do usuário
        workspace_id: ID do workspace
        
    Returns:
        List[Permission]: Lista de permissões
    """
```

## Fluxo de Dados
1. Workspace recebe requisição
2. Chama Auth para validar permissão
3. Auth retorna True/False
4. Workspace executa ou rejeita operação

## Tratamento de Erros
- Erros de autenticação: 401
- Erros de autorização: 403
- Erros de validação: 400

## Versionamento
- Breaking changes: Incrementa versão major
- Novos campos opcionais: Incrementa versão minor
- Bug fixes: Incrementa versão patch
```

### 3.2 Contrato Agents ↔ AI

```markdown
# Contrato: Agents ↔ AI

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo

## Visão Geral
Define como agentes interagem com o módulo AI para processamento de linguagem natural.

## Interface

### Agents → AI

#### Método: `process_prompt`
```python
async def process_prompt(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4"
) -> AIResponse:
    """
    Processa prompt usando modelo de IA.
    
    Args:
        prompt: Texto do prompt
        context: Contexto adicional
        model: Modelo a usar
        
    Returns:
        AIResponse: Resposta processada
    """
```

#### Método: `generate_code`
```python
async def generate_code(
    specification: str,
    language: str,
    context: Optional[Dict[str, Any]] = None
) -> CodeGenerationResponse:
    """
    Gera código baseado em especificação.
    
    Args:
        specification: Especificação do código
        language: Linguagem de programação
        context: Contexto do projeto
        
    Returns:
        CodeGenerationResponse: Código gerado
    """
```

### AI → Agents

#### Evento: `ai_response_ready`
```python
class AIResponseEvent:
    request_id: str
    response: AIResponse
    timestamp: datetime
    model_used: str
```

## Fluxo de Dados
1. Agente envia prompt para AI
2. AI processa e retorna resposta
3. Agente processa resposta
4. Agente executa ação baseada na resposta

## Tratamento de Erros
- Rate limit: 429
- Modelo indisponível: 503
- Prompt inválido: 400
- Timeout: 408

## Versionamento
- Mudanças no formato de resposta: Versão major
- Novos parâmetros opcionais: Versão minor
- Otimizações: Versão patch
```

## 4. Contratos entre Agentes

### 4.1 Contrato Generator ↔ Reviewer

```markdown
# Contrato: Generator ↔ Reviewer

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo

## Visão Geral
Define como o agente Generator envia código para o Reviewer e recebe feedback.

## Interface

### Generator → Reviewer

#### Evento: `code_generated`
```python
class CodeGeneratedEvent:
    session_id: str
    code: str
    language: str
    context: Dict[str, Any]
    requirements: List[str]
    timestamp: datetime
```

### Reviewer → Generator

#### Evento: `code_reviewed`
```python
class CodeReviewedEvent:
    session_id: str
    original_code: str
    approved: bool
    score: float  # 0.0 a 1.0
    suggestions: List[str]
    issues: List[CodeIssue]
    timestamp: datetime

class CodeIssue:
    line: int
    column: int
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: Optional[str]
```

## Fluxo de Dados
1. Generator produz código
2. Emite evento `code_generated`
3. Reviewer analisa código
4. Emite evento `code_reviewed`
5. Generator ajusta código se necessário

## Tratamento de Erros
- Código inválido: Rejeita com issues
- Timeout na análise: Retorna erro
- Falha na análise: Retorna erro genérico

## Versionamento
- Mudanças no formato de eventos: Versão major
- Novos campos opcionais: Versão minor
- Melhorias na análise: Versão patch
```

### 4.2 Contrato Reviewer ↔ Tester

```markdown
# Contrato: Reviewer ↔ Tester

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo

## Visão Geral
Define como o Reviewer envia código aprovado para o Tester.

## Interface

### Reviewer → Tester

#### Evento: `code_approved`
```python
class CodeApprovedEvent:
    session_id: str
    code: str
    language: str
    test_requirements: List[str]
    context: Dict[str, Any]
    timestamp: datetime
```

### Tester → Reviewer

#### Evento: `tests_completed`
```python
class TestsCompletedEvent:
    session_id: str
    original_code: str
    tests_passed: bool
    test_results: List[TestResult]
    coverage: float
    performance_metrics: Optional[Dict[str, Any]]
    timestamp: datetime

class TestResult:
    test_name: str
    passed: bool
    execution_time: float
    error_message: Optional[str]
```

## Fluxo de Dados
1. Reviewer aprova código
2. Emite evento `code_approved`
3. Tester executa testes
4. Emite evento `tests_completed`
5. Reviewer decide se código está pronto

## Tratamento de Erros
- Testes falharam: Retorna resultados com falhas
- Erro na execução: Retorna erro específico
- Timeout: Retorna timeout

## Versionamento
- Mudanças no formato de eventos: Versão major
- Novos tipos de teste: Versão minor
- Otimizações: Versão patch
```

## 5. Contratos com APIs Externas

### 5.1 Contrato OpenAI API

```markdown
# Contrato: OpenAI API

## Metadados
- **Versão**: 1.0.0
- **Data**: 2024-01-15
- **Status**: Ativo
- **API Version**: v1

## Visão Geral
Define como a plataforma interage com a OpenAI API.

## Interface

### Plataforma → OpenAI

#### Endpoint: `/v1/chat/completions`
```python
class OpenAIRequest:
    model: str = "gpt-4"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False

class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str
```

### OpenAI → Plataforma

#### Response
```python
class OpenAIResponse:
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

class Choice:
    index: int
    message: ChatMessage
    finish_reason: str

class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

## Tratamento de Erros
- Rate limit: 429 (retry after X seconds)
- Quota exceeded: 429
- Invalid request: 400
- Authentication: 401
- Server error: 500

## Rate Limits
- Requests per minute: 60
- Tokens per minute: 150,000
- Requests per day: 10,000

## Versionamento
- Seguir versionamento da OpenAI
- Breaking changes: Atualizar versão major
- Novos modelos: Versão minor
```

## 6. Validação de Contratos

### 6.1 Validação Automática

```python
# Exemplo de validação de contrato
from typing import Protocol

class ContractValidator(Protocol):
    def validate_request(self, data: dict) -> bool:
        """Valida se request está conforme contrato."""
        pass
    
    def validate_response(self, data: dict) -> bool:
        """Valida se response está conforme contrato."""
        pass

class AuthWorkspaceContractValidator:
    def validate_request(self, data: dict) -> bool:
        required_fields = ["user_id", "workspace_id", "operation"]
        return all(field in data for field in required_fields)
    
    def validate_response(self, data: dict) -> bool:
        return isinstance(data, bool)
```

### 6.2 Testes de Contrato

```python
import pytest
from app.contracts.validators import AuthWorkspaceContractValidator

class TestAuthWorkspaceContract:
    def test_validate_request_success(self):
        validator = AuthWorkspaceContractValidator()
        data = {
            "user_id": "123",
            "workspace_id": "456",
            "operation": "READ"
        }
        assert validator.validate_request(data) is True
    
    def test_validate_request_missing_field(self):
        validator = AuthWorkspaceContractValidator()
        data = {
            "user_id": "123",
            "workspace_id": "456"
            # Missing "operation"
        }
        assert validator.validate_request(data) is False
```

## 7. Versionamento de Contratos

### 7.1 Semantic Versioning

- **Major (X.0.0)**: Breaking changes
- **Minor (X.Y.0)**: Novas funcionalidades compatíveis
- **Patch (X.Y.Z)**: Bug fixes compatíveis

### 7.2 Compatibilidade

- **Backward Compatible**: Versões antigas funcionam com novas
- **Forward Compatible**: Versões novas funcionam com antigas
- **Breaking Change**: Incompatibilidade entre versões

### 7.3 Migração

```markdown
## Migração v1.0.0 → v2.0.0

### Breaking Changes
- Campo `old_field` removido
- Novo campo obrigatório `new_field`
- Mudança no formato de `response_data`

### Guia de Migração
1. Atualizar código para usar `new_field`
2. Remover referências a `old_field`
3. Atualizar parsing de `response_data`
4. Testar compatibilidade

### Timeline
- v1.0.0: Deprecated em 2024-02-01
- v2.0.0: Disponível em 2024-02-15
- v1.0.0: Removido em 2024-03-01
```

## 8. Monitoramento de Contratos

### 8.1 Métricas

- Taxa de sucesso das chamadas
- Tempo de resposta
- Taxa de erro por tipo
- Uso de versões

### 8.2 Alertas

- Falha em contrato: Alerta imediato
- Degradação de performance: Alerta em 5min
- Uso de versão deprecated: Alerta diário

## 9. Compliance

### 9.1 Checklist

Antes de implementar qualquer comunicação:

- [ ] Contrato documentado
- [ ] Validação implementada
- [ ] Testes criados
- [ ] Versionamento definido
- [ ] Monitoramento configurado
- [ ] Documentação atualizada

### 9.2 Revisão

- Contratos devem ser revisados em PRs
- Mudanças de contrato requerem aprovação de arquiteto
- Validação automática via CI/CD

---

**Importante**: Contratos são **obrigatórios** e devem ser seguidos rigorosamente. Violações resultam em falha de sistema e devem ser corrigidas imediatamente.


