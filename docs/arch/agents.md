# Arquitetura – Sistema de Agentes de Desenvolvimento

## 🎯 **Visão Geral**

O sistema de agentes é o **coração da plataforma**, permitindo que desenvolvedores conversem naturalmente com assistentes IA especializados para gerar, revisar e otimizar código automaticamente.

## 🏗️ **Arquitetura dos Agentes**

### **Estrutura de Módulos**
```
app/api/agents/
├── types.py          # Tipos de agentes e capacidades
├── schemas.py        # Schemas de chat e comunicação
├── services.py       # Lógica de negócio dos agentes
└── routes.py         # Endpoints da API
```

### **Componentes Principais**

#### 1. **AgentProfile** - Perfil do Agente
```python
@dataclass
class AgentProfile:
    id: str                    # Identificador único
    name: str                  # Nome amigável
    type: AgentType           # Tipo de agente
    description: str          # Descrição das capacidades
    capabilities: List[AgentCapability]  # Habilidades específicas
    system_prompt: str        # Prompt do sistema para OpenAI
    model: str               # Modelo OpenAI (gpt-4, gpt-3.5-turbo)
    temperature: float       # Criatividade (0.0-1.0)
    max_tokens: int          # Limite de tokens
```

#### 2. **Tipos de Agentes Disponíveis**

| Tipo | ID | Função Principal | Capacidades |
|------|----|------------------|-------------|
| **Gerador de Código** | `code_gen` | Criar código novo | Leitura, escrita, análise, sugestões |
| **Revisor de Código** | `code_review` | Analisar código existente | Leitura, análise, sugestões |
| **Gerador de Testes** | `test_gen` | Criar testes automáticos | Leitura, escrita, geração de testes |
| **Assistente de Debug** | `debugger` | Resolver problemas | Análise, identificação de bugs |

#### 3. **Capacidades dos Agentes**

```python
class AgentCapability(str, Enum):
    READ_CODE = "read_code"           # Ler arquivos de código
    WRITE_CODE = "write_code"         # Escrever/editar código
    EXECUTE_CODE = "execute_code"     # Executar código
    ANALYZE_CODE = "analyze_code"     # Analisar código
    GENERATE_TESTS = "generate_tests" # Gerar testes
    GENERATE_DOCS = "generate_docs"   # Gerar documentação
    SUGGEST_IMPROVEMENTS = "suggest_improvements"  # Sugerir melhorias
```

## 💬 **Sistema de Chat**

### **Fluxo de Conversação**

1. **Criação de Sessão**
   ```http
   POST /v1/agents/sessions
   {
     "agent_id": "code_gen",
     "context": {
       "workspace_path": "/projeto",
       "current_file": "main.py",
       "language": "python"
     }
   }
   ```

2. **Envio de Mensagem**
   ```http
   POST /v1/agents/chat
   {
     "message": "Crie uma função para calcular fibonacci",
     "agent_id": "code_gen",
     "include_code_context": true
   }
   ```

3. **Resposta do Agente**
   ```json
   {
     "message_id": "uuid",
     "content": "Aqui está a função Fibonacci...",
     "agent_id": "code_gen",
     "agent_name": "Gerador de Código",
     "code_blocks": [
       {
         "language": "python",
         "code": "def fibonacci(n): ..."
       }
     ],
     "suggestions": [
       "Considere adicionar memoização",
       "Adicione tratamento de erros"
     ]
   }
   ```

### **Contexto Inteligente**

Os agentes têm acesso ao contexto do projeto:
- **Arquivos atuais** - Código do workspace
- **Linguagem** - Python, JavaScript, etc.
- **Estrutura** - Diretórios e arquivos do projeto
- **Histórico** - Conversas anteriores da sessão

## 🔧 **Serviços dos Agentes**

### **1. AgentService**
- Gerenciamento de agentes disponíveis
- Criação e controle de sessões de chat
- Persistência de conversas

### **2. CodeGenerationService**
- Geração de código usando OpenAI
- Integração com contexto do workspace
- Validação e formatação de código

### **3. CodeReviewService**
- Análise automática de código
- Identificação de problemas
- Sugestões de melhoria

### **4. ChatService**
- Processamento de mensagens
- Integração com OpenAI
- Gerenciamento de contexto

## 🤖 **Integração com OpenAI**

### **System Prompts Especializados**

Cada agente tem um prompt específico otimizado para sua função:

#### **Gerador de Código**
```
Você é um assistente de desenvolvimento especializado em gerar código de alta qualidade.

Sua função é:
- Gerar código limpo, bem documentado e seguindo boas práticas
- Entender o contexto do projeto e manter consistência
- Explicar o código gerado de forma clara
- Sugerir melhorias e otimizações

Sempre que gerar código:
1. Inclua comentários explicativos
2. Siga as convenções da linguagem
3. Considere casos extremos e tratamento de erros
4. Mantenha o código legível e manutenível
```

#### **Revisor de Código**
```
Você é um revisor de código experiente com foco em qualidade e boas práticas.

Sua função é:
- Analisar código existente em busca de problemas
- Sugerir melhorias de performance, legibilidade e manutenibilidade
- Identificar bugs potenciais e vulnerabilidades
- Recomendar refatorações quando necessário

Ao revisar código:
1. Seja construtivo e educativo
2. Explique o "porquê" das sugestões
3. Priorize problemas críticos
4. Considere o contexto do projeto
```

## 📊 **Endpoints da API**

### **Gestão de Agentes**
- `GET /v1/agents/` - Lista agentes disponíveis
- `GET /v1/agents/{agent_id}` - Informações de um agente

### **Sessões de Chat**
- `POST /v1/agents/sessions` - Criar sessão
- `GET /v1/agents/sessions` - Listar sessões do usuário
- `GET /v1/agents/sessions/{session_id}` - Obter sessão específica

### **Conversação**
- `POST /v1/agents/chat` - Enviar mensagem para agente

### **Geração de Código**
- `POST /v1/agents/generate-code` - Gerar código específico
- `POST /v1/agents/review-code` - Revisar código existente

### **Health Check**
- `GET /v1/agents/health` - Status dos agentes

## 🔒 **Segurança**

### **Controle de Acesso**
- Autenticação obrigatória para todos os endpoints
- Verificação de permissões por usuário
- Rate limiting por usuário e agente

### **Sandbox de Execução**
- Código gerado é executado em ambiente isolado
- Limitações de recursos (CPU, memória, tempo)
- Bloqueio de operações perigosas

### **Auditoria**
- Logs de todas as interações com agentes
- Rastreamento de código gerado
- Histórico de sessões e conversas

## 🚀 **Roadmap**

### **Fase 1 - Básico** ✅
- [x] Estrutura base dos agentes
- [x] Tipos de agentes predefinidos
- [x] Sistema de chat
- [x] Endpoints da API

### **Fase 2 - Integração OpenAI** 🔄
- [ ] Integração real com OpenAI API
- [ ] Prompts otimizados por agente
- [ ] Geração de código funcional
- [ ] Revisão automática de código

### **Fase 3 - Workspace Integration** 📋
- [ ] Leitura de arquivos do projeto
- [ ] Escrita de código no workspace
- [ ] Execução segura de código
- [ ] Versionamento automático

### **Fase 4 - Interface Avançada** 📋
- [ ] UI de chat com agentes
- [ ] Visualização de código gerado
- [ ] Execução interativa
- [ ] Histórico de conversas

### **Fase 5 - Agentes Especializados** 📋
- [ ] Agente de arquitetura
- [ ] Agente de performance
- [ ] Agente de segurança
- [ ] Agente de documentação

