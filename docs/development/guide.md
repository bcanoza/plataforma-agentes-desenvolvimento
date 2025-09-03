# Guia de Desenvolvimento - Plataforma de Agentes

## 🎯 **Visão Geral**

Este guia fornece instruções completas para desenvolver, testar e contribuir com a plataforma de agentes de desenvolvimento.

## 🏗️ **Estrutura do Projeto**

### **Organização de Diretórios**
```
app/
├── api/                    # Nova estrutura modular
│   ├── auth/              # Autenticação
│   ├── agents/            # Sistema de agentes
│   ├── workspace/         # Gestão de projetos
│   ├── code/              # Operações de código
│   ├── execution/         # Execução segura
│   ├── ai/                # Integração OpenAI
│   └── development/       # Ferramentas de dev
├── controllers/           # Estrutura legada (em migração)
├── services/              # Serviços de negócio
├── config/                # Configurações
├── security/              # Segurança e JWT
├── core/                  # Núcleo da aplicação
└── main.py               # Ponto de entrada
```

### **Padrões de Arquitetura**

#### **1. Estrutura de Módulos**
Cada módulo da API segue o padrão:
```
api/{module}/
├── __init__.py           # Documentação do módulo
├── routes.py            # Endpoints da API
├── schemas.py           # Schemas Pydantic
├── services.py          # Lógica de negócio
├── dependencies.py      # Dependências FastAPI
└── types.py            # Tipos e enums (opcional)
```

#### **2. Separação de Responsabilidades**
- **Routes**: Apenas endpoints e validação
- **Services**: Lógica de negócio
- **Schemas**: Contratos de dados
- **Dependencies**: Injeção de dependências

## 🚀 **Configuração do Ambiente**

### **Pré-requisitos**
- Python 3.11+
- Docker e Docker Compose
- PostgreSQL 15+
- Redis 7+

### **Instalação**
```bash
# Clone o repositório
git clone <repository-url>
cd plataforma-agentes

# Configure o ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicie os serviços
docker-compose up -d

# Instale dependências Python
pip install -r requirements.txt
```

### **Variáveis de Ambiente**
```bash
# Banco de dados
DATABASE_URL=postgresql://user:pass@localhost:5432/plataforma

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=RS256

# OpenAI
OPENAI_API_KEY=your-openai-key

# Aplicação
DEBUG=true
LOG_LEVEL=INFO
COOKIE_DOMAIN=.localhost
```

## 🧪 **Desenvolvimento**

### **Executando Localmente**
```bash
# Desenvolvimento com hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testes
pytest tests/ -v

# Linting
black app/
flake8 app/
mypy app/
```

### **Estrutura de Testes**
```
tests/
├── unit/                 # Testes unitários
│   ├── test_agents.py
│   ├── test_auth.py
│   └── test_services.py
├── integration/          # Testes de integração
│   ├── test_api.py
│   └── test_workflows.py
└── fixtures/             # Dados de teste
    ├── users.json
    └── projects.json
```

### **Executando Testes**
```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/unit/test_agents.py

# Com cobertura
pytest --cov=app --cov-report=html

# Testes de integração
pytest tests/integration/ -m integration
```

## 🤖 **Desenvolvendo Agentes**

### **Criando um Novo Agente**

#### **1. Definir o Tipo**
```python
# app/api/agents/types.py
class AgentType(str, Enum):
    NEW_AGENT = "new_agent"

class AgentCapability(str, Enum):
    NEW_CAPABILITY = "new_capability"
```

#### **2. Criar o Perfil**
```python
# app/api/agents/types.py
AGENTS["new_agent"] = AgentProfile(
    id="new_agent",
    name="Novo Agente",
    type=AgentType.NEW_AGENT,
    description="Descrição do novo agente",
    capabilities=[
        AgentCapability.READ_CODE,
        AgentCapability.WRITE_CODE,
        AgentCapability.NEW_CAPABILITY
    ],
    system_prompt="""Você é um novo agente especializado em...
    
    Sua função é:
    - Fazer X
    - Fazer Y
    - Fazer Z
    
    Sempre que fizer algo:
    1. Passo 1
    2. Passo 2
    3. Passo 3"""
)
```

#### **3. Implementar Serviço**
```python
# app/api/agents/services.py
class NewAgentService:
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service
    
    async def new_agent_action(self, request: NewAgentRequest) -> NewAgentResponse:
        # Implementar lógica específica
        pass
```

#### **4. Adicionar Endpoints**
```python
# app/api/agents/routes.py
@router.post("/new-agent-action", response_model=NewAgentResponse)
async def new_agent_action(
    request: NewAgentRequest,
    current: CurrentUser = Depends(require_user)
):
    service = NewAgentService(agent_service)
    return await service.new_agent_action(request)
```

### **Integração com OpenAI**

#### **1. Configurar Cliente**
```python
# app/api/ai/services.py
import openai

class OpenAIService:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
```

#### **2. Usar em Agentes**
```python
# app/api/agents/services.py
async def send_message(self, session_id: str, message: str) -> ChatResponse:
    # Preparar mensagens
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": message}
    ]
    
    # Chamar OpenAI
    response = await self.openai_service.chat_completion(
        messages=messages,
        model=agent.model,
        temperature=agent.temperature
    )
    
    return ChatResponse(content=response, ...)
```

## 📁 **Desenvolvendo Módulos**

### **Criando um Novo Módulo**

#### **1. Estrutura Base**
```bash
mkdir -p app/api/new_module
touch app/api/new_module/__init__.py
touch app/api/new_module/routes.py
touch app/api/new_module/schemas.py
touch app/api/new_module/services.py
```

#### **2. Schemas**
```python
# app/api/new_module/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class NewModuleRequest(BaseModel):
    field1: str
    field2: Optional[int] = None

class NewModuleResponse(BaseModel):
    result: str
    metadata: dict
```

#### **3. Services**
```python
# app/api/new_module/services.py
class NewModuleService:
    def __init__(self):
        pass
    
    async def process_request(self, request: NewModuleRequest) -> NewModuleResponse:
        # Implementar lógica
        return NewModuleResponse(result="success", metadata={})
```

#### **4. Routes**
```python
# app/api/new_module/routes.py
from fastapi import APIRouter, Depends
from app.api.auth.dependencies import require_user

router = APIRouter(prefix="/v1/new-module", tags=["NewModule"])

@router.post("/", response_model=NewModuleResponse)
async def process(
    request: NewModuleRequest,
    current: CurrentUser = Depends(require_user)
):
    service = NewModuleService()
    return await service.process_request(request)
```

#### **5. Registrar no Core**
```python
# app/core/api_loader.py
def include_api_modules(app: FastAPI):
    # ... outros módulos
    from app.api.new_module.routes import router as new_module_router
    app.include_router(new_module_router)
```

## 🔒 **Segurança**

### **Autenticação**
```python
# Usar dependências de autenticação
from app.api.auth.dependencies import require_user, require_admin

@router.get("/protected")
async def protected_endpoint(current: CurrentUser = Depends(require_user)):
    return {"user_id": current["sub"]}

@router.get("/admin-only")
async def admin_endpoint(current: CurrentUser = Depends(require_admin)):
    return {"admin": True}
```

### **Validação de Dados**
```python
# Usar schemas Pydantic para validação
from pydantic import BaseModel, validator

class UserRequest(BaseModel):
    email: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Invalid age')
        return v
```

### **Rate Limiting**
```python
# Implementar rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/")
@limiter.limit("10/minute")
async def rate_limited_endpoint(request: Request):
    return {"message": "Success"}
```

## 📊 **Monitoramento**

### **Logging**
```python
# Usar logger configurado
from app.core.logging_config import get_logger

logger = get_logger("module_name")

@router.post("/")
async def endpoint():
    logger.info("Processing request")
    try:
        # Lógica
        logger.info("Request processed successfully")
    except Exception as e:
        logger.exception("Error processing request")
        raise
```

### **Métricas**
```python
# Adicionar métricas
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

@router.post("/")
async def endpoint():
    REQUEST_COUNT.labels(method='POST', endpoint='/endpoint').inc()
    
    with REQUEST_DURATION.time():
        # Lógica
        pass
```

## 🚀 **Deploy**

### **Docker**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/plataforma
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: plataforma
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
  
  redis:
    image: redis:7-alpine
```

## 📖 **Documentação**

### **Docstrings**
```python
async def generate_code(
    prompt: str,
    agent_id: str,
    language: str = "python"
) -> CodeGenerationResponse:
    """
    Gera código usando agente específico.
    
    Args:
        prompt: Descrição do código a ser gerado
        agent_id: ID do agente a ser usado
        language: Linguagem de programação
        
    Returns:
        Resposta com código gerado e metadados
        
    Raises:
        ValueError: Se agente não for encontrado
        OpenAIError: Se houver erro na API OpenAI
    """
    pass
```

### **OpenAPI**
```python
# Adicionar documentação aos endpoints
@router.post(
    "/generate-code",
    response_model=CodeGenerationResponse,
    summary="Gerar código",
    description="Gera código usando agente IA específico",
    responses={
        200: {"description": "Código gerado com sucesso"},
        400: {"description": "Erro na requisição"},
        404: {"description": "Agente não encontrado"}
    }
)
async def generate_code(request: CodeGenerationRequest):
    pass
```

## 🧪 **Testes**

### **Testes Unitários**
```python
# tests/unit/test_agents.py
import pytest
from app.api.agents.services import AgentService

@pytest.fixture
def agent_service():
    return AgentService()

def test_get_agent(agent_service):
    agent = agent_service.get_agent("code_gen")
    assert agent is not None
    assert agent.id == "code_gen"

def test_get_nonexistent_agent(agent_service):
    agent = agent_service.get_agent("nonexistent")
    assert agent is None
```

### **Testes de Integração**
```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_agents():
    response = client.get("/v1/agents/")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) > 0
```

## 🔄 **Migração da Estrutura Legada**

### **Migrando Controllers**
1. **Identificar responsabilidades** do controller
2. **Separar em módulos** apropriados
3. **Criar schemas** Pydantic
4. **Implementar services** de negócio
5. **Criar routes** FastAPI
6. **Testar** funcionalidade
7. **Remover** controller legado

### **Exemplo de Migração**
```python
# ANTES: app/controllers/fs_controller.py
@router.get("/files/{path:path}")
async def read_file(path: str):
    # Lógica misturada
    pass

# DEPOIS: app/api/code/routes.py
@router.get("/files/{path:path}")
async def read_file(
    path: str,
    current: CurrentUser = Depends(require_user)
):
    service = CodeService()
    return await service.read_file(path, current["sub"])
```

## 📋 **Checklist de Desenvolvimento**

### **Antes de Commitar**
- [ ] Código formatado com `black`
- [ ] Linting passou com `flake8`
- [ ] Type checking passou com `mypy`
- [ ] Testes unitários passaram
- [ ] Testes de integração passaram
- [ ] Documentação atualizada
- [ ] Logs apropriados adicionados

### **Antes de Fazer PR**
- [ ] Funcionalidade testada manualmente
- [ ] Performance verificada
- [ ] Segurança revisada
- [ ] Compatibilidade com versões anteriores
- [ ] Changelog atualizado
- [ ] Review de código solicitado

## 🆘 **Troubleshooting**

### **Problemas Comuns**

#### **Erro de Import**
```bash
ModuleNotFoundError: No module named 'app'
```
**Solução**: Verificar PYTHONPATH e estrutura de diretórios

#### **Erro de Autenticação**
```bash
401 Unauthorized
```
**Solução**: Verificar JWT tokens e configurações de segurança

#### **Erro de Banco**
```bash
ConnectionError: database connection failed
```
**Solução**: Verificar DATABASE_URL e status do PostgreSQL

#### **Erro de OpenAI**
```bash
OpenAIError: API key invalid
```
**Solução**: Verificar OPENAI_API_KEY nas variáveis de ambiente

