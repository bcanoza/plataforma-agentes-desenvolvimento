# API Overview - Plataforma de Agentes de Desenvolvimento

## 🎯 **Visão Geral**

A API da plataforma é organizada em **módulos especializados** que trabalham em conjunto para fornecer uma experiência completa de desenvolvimento assistido por IA.

## 🏗️ **Estrutura da API**

### **Organização Modular**
```
app/api/
├── auth/              # Autenticação e usuários
├── agents/            # Sistema de agentes IA
├── workspace/         # Gestão de projetos
├── code/              # Operações de código
├── execution/         # Execução segura
├── ai/                # Integração OpenAI
└── development/       # Ferramentas de desenvolvimento
```

### **Padrões de Nomenclatura**
- **Rotas**: `/v1/{module}/{resource}`
- **Schemas**: `{Module}{Resource}Request/Response`
- **Services**: `{Module}Service`
- **Dependencies**: `require_{role}`

## 📚 **Módulos da API**

### **1. Auth Module** (`/v1/auth/`)
**Responsabilidade**: Autenticação, usuários e sessões

**Endpoints**:
- `POST /login` - Autenticação de usuário
- `POST /refresh` - Renovação de tokens
- `POST /logout` - Encerramento de sessão
- `POST /request-password-reset` - Solicitar reset de senha
- `POST /confirm-password-reset` - Confirmar reset de senha
- `GET /validate` - Validar token
- `GET /.well-known/jwks.json` - Chaves públicas JWT

**Schemas**:
- `LoginRequest/Response`
- `User`
- `RequestPasswordResetRequest/Response`
- `ConfirmPasswordResetRequest/Response`

### **2. Agents Module** (`/v1/agents/`)
**Responsabilidade**: Conversação e gerenciamento de agentes IA

**Endpoints**:
- `GET /` - Lista agentes disponíveis
- `GET /{agent_id}` - Informações de um agente
- `POST /sessions` - Criar sessão de chat
- `GET /sessions` - Listar sessões do usuário
- `GET /sessions/{session_id}` - Obter sessão específica
- `POST /chat` - Enviar mensagem para agente
- `POST /generate-code` - Gerar código específico
- `POST /review-code` - Revisar código existente
- `GET /health` - Status dos agentes

**Schemas**:
- `ChatRequest/Response`
- `AgentInfo`
- `CodeGenerationRequest/Response`
- `CodeReviewRequest/Response`
- `ChatSession`

### **3. Workspace Module** (`/v1/workspace/`)
**Responsabilidade**: Gestão de projetos e estrutura de arquivos

**Endpoints**:
- `GET /projects` - Listar projetos do usuário
- `POST /projects` - Criar novo projeto
- `GET /projects/{project_id}` - Obter projeto específico
- `PUT /projects/{project_id}` - Atualizar projeto
- `DELETE /projects/{project_id}` - Excluir projeto
- `GET /projects/{project_id}/structure` - Estrutura de arquivos
- `POST /projects/{project_id}/sync` - Sincronizar com filesystem

**Schemas**:
- `Project`
- `ProjectStructure`
- `CreateProjectRequest`
- `UpdateProjectRequest`

### **4. Code Module** (`/v1/code/`)
**Responsabilidade**: Operações de leitura e escrita de código

**Endpoints**:
- `GET /files/{path:path}` - Ler arquivo
- `PUT /files/{path:path}` - Escrever arquivo
- `POST /files/{path:path}` - Criar arquivo
- `DELETE /files/{path:path}` - Excluir arquivo
- `GET /directories/{path:path}` - Listar diretório
- `POST /directories/{path:path}` - Criar diretório
- `GET /search` - Buscar em arquivos
- `POST /validate` - Validar sintaxe

**Schemas**:
- `FileContent`
- `DirectoryListing`
- `FileOperation`
- `SearchRequest/Response`
- `ValidationResult`

### **5. Execution Module** (`/v1/execution/`)
**Responsabilidade**: Execução segura de código

**Endpoints**:
- `POST /run` - Executar código
- `GET /sessions/{session_id}` - Status da execução
- `POST /sessions/{session_id}/stop` - Parar execução
- `GET /sessions/{session_id}/output` - Obter output
- `GET /sessions/{session_id}/logs` - Obter logs

**Schemas**:
- `ExecutionRequest/Response`
- `ExecutionSession`
- `ExecutionOutput`
- `ExecutionLog`

### **6. AI Module** (`/v1/ai/`)
**Responsabilidade**: Integração com OpenAI

**Endpoints**:
- `POST /chat` - Chat direto com OpenAI
- `POST /completion` - Completar texto
- `POST /embedding` - Gerar embeddings
- `GET /models` - Listar modelos disponíveis
- `GET /usage` - Estatísticas de uso

**Schemas**:
- `ChatRequest/Response`
- `CompletionRequest/Response`
- `EmbeddingRequest/Response`
- `ModelInfo`
- `UsageStats`

### **7. Development Module** (`/v1/development/`)
**Responsabilidade**: Ferramentas de desenvolvimento

**Endpoints**:
- `POST /tests/run` - Executar testes
- `GET /tests/results` - Resultados de testes
- `POST /lint` - Análise de código
- `POST /format` - Formatação de código
- `GET /diagnostics` - Diagnósticos do sistema
- `POST /build` - Build do projeto

**Schemas**:
- `TestRequest/Response`
- `LintRequest/Response`
- `FormatRequest/Response`
- `DiagnosticResult`
- `BuildRequest/Response`

## 🔄 **Fluxos de Integração**

### **Fluxo de Geração de Código**
1. **Usuário** → `POST /v1/agents/chat` (prompt)
2. **Agente** → `GET /v1/code/files/{path}` (contexto)
3. **Agente** → `POST /v1/ai/chat` (OpenAI)
4. **Agente** → `POST /v1/code/files/{path}` (salvar código)
5. **Usuário** → `POST /v1/execution/run` (testar código)

### **Fluxo de Revisão de Código**
1. **Usuário** → `POST /v1/agents/review-code`
2. **Agente** → `GET /v1/code/files/{path}` (ler arquivo)
3. **Agente** → `POST /v1/ai/chat` (análise)
4. **Agente** → Retorna sugestões e melhorias

### **Fluxo de Execução Segura**
1. **Usuário** → `POST /v1/execution/run`
2. **Sistema** → Valida código
3. **Sistema** → Executa em sandbox
4. **Sistema** → Retorna output/erros
5. **Sistema** → Limpa recursos

## 🔒 **Segurança e Autenticação**

### **Autenticação**
- **JWT Tokens**: Acesso a todos os endpoints
- **Refresh Tokens**: Renovação automática
- **API Keys**: Para integrações externas

### **Autorização**
- **Usuários**: Acesso aos próprios recursos
- **Admins**: Acesso a recursos administrativos
- **Agentes**: Acesso controlado ao workspace

### **Rate Limiting**
- **Por usuário**: Limites individuais
- **Por endpoint**: Limites específicos
- **Por agente**: Limites de uso de IA

## 📊 **Monitoramento e Logs**

### **Métricas**
- **Uso de agentes**: Frequência e tipos
- **Geração de código**: Volume e qualidade
- **Execuções**: Sucesso/falha e performance
- **Recursos**: CPU, memória, storage

### **Logs**
- **Auditoria**: Todas as operações
- **Erros**: Stack traces e contexto
- **Performance**: Tempos de resposta
- **Segurança**: Tentativas de acesso

## 🚀 **Versionamento**

### **API Versioning**
- **v1**: Versão atual estável
- **v2**: Próxima versão em desenvolvimento
- **Backward Compatibility**: Manutenção de compatibilidade

### **Schema Evolution**
- **Additive Changes**: Novos campos opcionais
- **Breaking Changes**: Versões major
- **Deprecation**: Avisos de descontinuação

## 📖 **Documentação**

### **OpenAPI/Swagger**
- **Especificação**: OpenAPI 3.0.3
- **UI**: Interface interativa
- **Schemas**: Validação automática

### **Exemplos**
- **Requests**: Exemplos de uso
- **Responses**: Respostas esperadas
- **Error Codes**: Códigos de erro

### **Guias**
- **Getting Started**: Primeiros passos
- **Authentication**: Como autenticar
- **Agents**: Como usar agentes
- **Best Practices**: Boas práticas

