# Diretrizes de Documentação

## Visão Geral

Esta documentação estabelece diretrizes **obrigatórias** para documentação de código, APIs e agentes na Plataforma de Agentes de Desenvolvimento. Todas as contribuições devem seguir estas diretrizes.

## 1. Documentação de Código

### 1.1 Docstrings Obrigatórias

**TODOS** os módulos, classes, funções e métodos públicos devem ter docstrings seguindo o padrão Google Style:

```python
def process_user_data(user_id: str, data: dict) -> UserResponse:
    """
    Processa dados do usuário e retorna resposta formatada.
    
    Args:
        user_id: ID único do usuário
        data: Dados do usuário em formato dicionário
        
    Returns:
        UserResponse: Resposta processada com dados do usuário
        
    Raises:
        ValidationError: Se os dados não forem válidos
        UserNotFoundError: Se o usuário não existir
        
    Example:
        >>> response = process_user_data("123", {"name": "João"})
        >>> print(response.name)
        João
    """
```

### 1.2 Comentários de Código

- **Obrigatório**: Comentários para lógica complexa ou não óbvia
- **Obrigatório**: Explicação de algoritmos ou decisões de design
- **Proibido**: Comentários óbvios que apenas repetem o código

```python
# ✅ BOM: Explica o "porquê"
# Usar cache LRU para evitar consultas repetidas ao banco
@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str):
    pass

# ❌ RUIM: Apenas repete o código
# Incrementa o contador
counter += 1
```

### 1.3 Type Hints

**TODOS** os parâmetros e retornos devem ter type hints:

```python
from typing import List, Optional, Dict, Any

def create_agent(
    agent_type: AgentType,
    config: Dict[str, Any],
    dependencies: Optional[List[str]] = None
) -> Agent:
    """Cria um novo agente com configuração especificada."""
    pass
```

## 2. Documentação de APIs

### 2.1 Schemas Pydantic

**TODOS** os schemas devem ter:
- Descrição clara do campo
- Exemplos quando aplicável
- Validações documentadas

```python
class CreateAgentRequest(BaseModel):
    """Request para criação de novo agente."""
    
    name: str = Field(
        ..., 
        description="Nome único do agente",
        example="code-generator-v1",
        min_length=3,
        max_length=50
    )
    
    agent_type: AgentType = Field(
        ...,
        description="Tipo do agente conforme enum AgentType"
    )
    
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações específicas do agente"
    )
```

### 2.2 Endpoints

**TODOS** os endpoints devem ter:
- Descrição clara da funcionalidade
- Exemplos de request/response
- Códigos de erro possíveis
- Tags apropriadas

```python
@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=201,
    summary="Criar novo agente",
    description="Cria um novo agente de desenvolvimento com configuração especificada",
    tags=["agents", "management"]
)
async def create_agent(
    request: CreateAgentRequest,
    current_user: User = Depends(require_admin)
) -> AgentResponse:
    """
    Cria um novo agente de desenvolvimento.
    
    Args:
        request: Dados para criação do agente
        current_user: Usuário autenticado (deve ser admin)
        
    Returns:
        AgentResponse: Dados do agente criado
        
    Raises:
        400: Dados inválidos
        401: Não autenticado
        403: Sem permissão de admin
        409: Nome do agente já existe
    """
```

## 3. Documentação de Agentes

### 3.1 Perfil do Agente

**TODOS** os agentes devem ter documentação completa:

```python
class CodeGeneratorAgent:
    """
    Agente responsável por gerar código baseado em especificações.
    
    Capabilities:
        - Geração de código Python, JavaScript, TypeScript
        - Análise de requisitos
        - Criação de testes unitários
        - Documentação automática
        
    Dependencies:
        - OpenAI API (GPT-4)
        - Workspace Manager
        - Code Repository
        
    Input Format:
        - Especificação em linguagem natural
        - Contexto do projeto
        - Restrições técnicas
        
    Output Format:
        - Código gerado
        - Explicação da implementação
        - Sugestões de melhorias
    """
```

### 3.2 Contratos de Comunicação

**TODOS** os agentes devem documentar:
- Formato de entrada esperado
- Formato de saída produzido
- Dependências de outros agentes
- Eventos que emite/escuta

## 4. Documentação de Módulos

### 4.1 README por Módulo

**TODOS** os módulos devem ter `README.md` com:
- Propósito do módulo
- Como usar
- Dependências
- Exemplos de uso
- Changelog

### 4.2 Estrutura de Arquivos

```
app/api/agents/
├── README.md              # Documentação do módulo
├── __init__.py           # Exports públicos
├── types.py              # Tipos e enums
├── schemas.py            # Schemas Pydantic
├── services.py           # Lógica de negócio
├── routes.py             # Endpoints
├── dependencies.py       # Dependências FastAPI
└── contracts/            # Contratos com outros módulos
    ├── workspace.md      # Contrato com workspace
    └── ai.md            # Contrato com AI
```

## 5. Documentação de Contratos

### 5.1 Contratos entre Módulos

**TODOS** os módulos que dependem de outros devem ter contratos documentados:

```markdown
# Contrato: Agents ↔ Workspace

## Visão Geral
Este contrato define a comunicação entre o módulo Agents e Workspace.

## Dependências
- Agents depende de Workspace para operações de arquivo
- Workspace fornece API para Agents

## Interface
### Workspace → Agents
- `workspace.file_created(file_path: str)`
- `workspace.file_modified(file_path: str)`

### Agents → Workspace
- `workspace.create_file(path: str, content: str)`
- `workspace.read_file(path: str) -> str`

## Versionamento
- Versão atual: 1.0
- Breaking changes: Requer atualização de ambos os módulos
```

### 5.2 Contratos entre Agentes

```markdown
# Contrato: Generator ↔ Reviewer

## Visão Geral
Contrato de comunicação entre agente Generator e Reviewer.

## Fluxo de Dados
1. Generator produz código
2. Envia para Reviewer via evento
3. Reviewer analisa e retorna feedback
4. Generator ajusta baseado no feedback

## Formato de Dados
### Generator → Reviewer
```json
{
  "code": "string",
  "language": "python|javascript|typescript",
  "context": "string",
  "requirements": ["string"]
}
```

### Reviewer → Generator
```json
{
  "approved": boolean,
  "suggestions": ["string"],
  "score": number,
  "issues": ["string"]
}
```
```

## 6. Validação e Compliance

### 6.1 Checklist Obrigatório

Antes de qualquer commit, verificar:

- [ ] Docstrings em todas as funções públicas
- [ ] Type hints em todos os parâmetros
- [ ] Schemas Pydantic documentados
- [ ] Endpoints com descrição e exemplos
- [ ] README do módulo atualizado
- [ ] Contratos documentados
- [ ] Exemplos de uso funcionais

### 6.2 Ferramentas de Validação

```bash
# Validar docstrings
pydocstyle app/

# Validar type hints
mypy app/

# Validar schemas
python -m pydantic.tools.validate_schemas
```

## 7. Templates

### 7.1 Template de Módulo

```python
"""
Módulo [Nome do Módulo]

Descrição: [Descrição clara do propósito]

Dependencies:
    - [Lista de dependências]

Exports:
    - [Lista de exports públicos]

Version: 1.0.0
Author: [Nome do autor]
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# Schemas
class ModuleRequest(BaseModel):
    """Request template para o módulo."""
    pass

class ModuleResponse(BaseModel):
    """Response template para o módulo."""
    pass

# Services
class ModuleService:
    """Serviço principal do módulo."""
    
    def __init__(self):
        """Inicializa o serviço."""
        pass
    
    async def process(self, request: ModuleRequest) -> ModuleResponse:
        """
        Processa request do módulo.
        
        Args:
            request: Dados de entrada
            
        Returns:
            ModuleResponse: Resultado processado
        """
        pass
```

### 7.2 Template de Agente

```python
"""
Agente [Nome do Agente]

Tipo: [Generator|Reviewer|Tester|Debugger]
Capabilities: [Lista de capacidades]
Dependencies: [Lista de dependências]
"""

from app.api.agents.types import AgentType, AgentProfile

class [Nome]Agent:
    """Agente [descrição]."""
    
    def __init__(self):
        self.profile = AgentProfile(
            name="[nome]",
            agent_type=AgentType.[TIPO],
            capabilities=["[lista]"],
            dependencies=["[lista]"]
        )
    
    async def process(self, input_data: dict) -> dict:
        """
        Processa entrada do agente.
        
        Args:
            input_data: Dados de entrada
            
        Returns:
            dict: Resultado processado
        """
        pass
```

## 8. Manutenção

### 8.1 Atualizações

- Documentação deve ser atualizada junto com o código
- Breaking changes requerem atualização de contratos
- Versionamento semântico para contratos

### 8.2 Revisão

- Toda documentação deve ser revisada em PRs
- Validação automática via CI/CD
- Auditoria mensal de compliance

---

**Importante**: Esta documentação é **obrigatória** e deve ser seguida por todos os desenvolvedores. Violações resultam em rejeição de PRs.



