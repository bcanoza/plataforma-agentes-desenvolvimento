# 🤖 Plataforma de Agentes de Desenvolvimento

Uma **infraestrutura completa para agentes de desenvolvimento** que conversam com usuários e geram/editem código automaticamente usando IA.

## 🎯 **Visão Geral**

Esta plataforma permite que desenvolvedores **conversem naturalmente** com assistentes IA especializados para:

- 🧠 **Gerar código** - Python, JavaScript, TypeScript, etc.
- 🔍 **Revisar código** - Análise automática e sugestões
- 🧪 **Criar testes** - Testes unitários e de integração
- 🐛 **Debugar problemas** - Identificação e correção de bugs
- 📚 **Gerar documentação** - Docs automáticas e comentários

## ✨ **Características Principais**

### **🤖 Agentes IA Especializados**
- **Gerador de Código**: Cria código limpo e bem documentado
- **Revisor de Código**: Analisa e sugere melhorias
- **Gerador de Testes**: Cria testes abrangentes
- **Assistente de Debug**: Ajuda a resolver problemas

### **💬 Conversação Natural**
- Chat intuitivo com agentes especializados
- Contexto inteligente do projeto
- Histórico de conversas persistente
- Sugestões automáticas

### **🔒 Segurança Robusta**
- Sandbox seguro para execução de código
- Autenticação JWT com refresh tokens
- Rate limiting e proteção anti-brute force
- Auditoria completa de operações

### **🏗️ Arquitetura Modular**
- API REST bem estruturada
- Módulos especializados e escaláveis
- Integração com OpenAI GPT-4
- Suporte a múltiplas linguagens

## 🚀 **Quick Start**

### **Pré-requisitos**
- Python 3.11+
- Docker e Docker Compose
- PostgreSQL 15+
- Redis 7+
- Chave da API OpenAI

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

# Execute a aplicação
uvicorn app.main:app --reload
```

### **Configuração Básica**
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/plataforma
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-key
JWT_SECRET_KEY=your-secret-key
```

## 📚 **Documentação**

### **Arquitetura**
- [📖 Overview da Arquitetura](docs/arch/overview.md)
- [🤖 Sistema de Agentes](docs/arch/agents.md)
- [🔒 Segurança](docs/arch/security.md)

### **API**
- [🌐 API Overview](docs/api/overview.md)
- [📋 Schemas e Contratos](docs/documentation/schemas.md)

### **Desenvolvimento**
- [🛠️ Guia de Desenvolvimento](docs/development/guide.md)
- [🧪 Testes](docs/development/testing.md)
- [🚀 Deploy](docs/ops/deployment.md)

## 🏗️ **Estrutura do Projeto**

```
app/
├── api/                    # Nova estrutura modular
│   ├── auth/              # Autenticação e usuários
│   ├── agents/            # Sistema de agentes IA
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

## 🔄 **Fluxo de Uso**

### **1. Autenticação**
```bash
POST /v1/auth/login
{
  "username": "usuario",
  "password": "senha"
}
```

### **2. Conversar com Agente**
```bash
POST /v1/agents/chat
{
  "message": "Crie uma função para calcular fibonacci",
  "agent_id": "code_gen"
}
```

### **3. Gerar Código**
```bash
POST /v1/agents/generate-code
{
  "prompt": "Função de ordenação quicksort",
  "agent_id": "code_gen",
  "language": "python"
}
```

### **4. Executar Código**
```bash
POST /v1/execution/run
{
  "code": "def fibonacci(n): ...",
  "language": "python"
}
```

## 🎯 **Tipos de Agentes**

| Agente | ID | Função | Capacidades |
|--------|----|---------|-------------|
| **Gerador de Código** | `code_gen` | Criar código novo | Leitura, escrita, análise, sugestões |
| **Revisor de Código** | `code_review` | Analisar código existente | Leitura, análise, sugestões |
| **Gerador de Testes** | `test_gen` | Criar testes automáticos | Leitura, escrita, geração de testes |
| **Assistente de Debug** | `debugger` | Resolver problemas | Análise, identificação de bugs |

## 🔒 **Segurança**

### **Autenticação**
- JWT tokens minimalistas (sem PII)
- Refresh tokens opacos rotacionados
- Rate limiting por usuário e IP
- Proteção anti-brute force

### **Execução Segura**
- Sandbox isolado para código
- Limites de recursos (CPU, memória, tempo)
- Bloqueio de operações perigosas
- Auditoria completa de execuções

### **Proteção de Dados**
- Criptografia em trânsito (TLS 1.3)
- Criptografia em repouso (AES-256)
- Senhas com bcrypt
- Logs sem dados sensíveis

## 🧪 **Testes**

```bash
# Testes unitários
pytest tests/unit/ -v

# Testes de integração
pytest tests/integration/ -v

# Com cobertura
pytest --cov=app --cov-report=html

# Linting
black app/
flake8 app/
mypy app/
```

## 🚀 **Deploy**

### **Docker**
```bash
# Build da imagem
docker build -t plataforma-agentes .

# Executar container
docker run -p 8000:8000 plataforma-agentes
```

### **Docker Compose**
```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

## 📊 **Monitoramento**

### **Métricas**
- Uso de agentes por usuário
- Geração de código (volume/qualidade)
- Execuções (sucesso/falha)
- Recursos (CPU, memória, storage)

### **Logs**
- Auditoria de operações
- Erros e stack traces
- Performance e tempos de resposta
- Tentativas de acesso suspeitas

## 🤝 **Contribuição**

### **Como Contribuir**
1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente com testes
4. Faça commit das mudanças
5. Abra um Pull Request

### **Padrões de Código**
- Python 3.11+ com type hints
- FastAPI para API REST
- Pydantic para validação
- Black para formatação
- Pytest para testes

### **Estrutura de Commits**
```
feat: adicionar novo agente de documentação
fix: corrigir bug na execução de código
docs: atualizar documentação da API
test: adicionar testes para geração de código
```

## 📋 **Roadmap**

### **Fase 1 - Básico** ✅
- [x] Estrutura base dos agentes
- [x] Sistema de autenticação
- [x] API REST modular
- [x] Documentação completa

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

## 📄 **Licença**

Este projeto está licenciado sob a [MIT License](LICENSE).

## 🆘 **Suporte**

### **Problemas Comuns**
- [Troubleshooting](docs/development/guide.md#troubleshooting)
- [FAQ](docs/faq.md)

### **Contato**
- 📧 Email: suporte@plataforma-agentes.com
- 💬 Discord: [Servidor da Comunidade](https://discord.gg/plataforma-agentes)
- 📖 Wiki: [Documentação Completa](docs/)

## 🙏 **Agradecimentos**

- OpenAI pela API GPT-4
- FastAPI pela excelente framework
- Comunidade Python pelo suporte
- Contribuidores do projeto

---

**Desenvolvido com ❤️ para a comunidade de desenvolvedores**

