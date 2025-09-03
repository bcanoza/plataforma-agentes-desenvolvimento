# Arquitetura – Overview (Plataforma de Agentes de Desenvolvimento)

A plataforma é uma **infraestrutura completa para agentes de desenvolvimento** que conversam com usuários e geram/editem código automaticamente. Composta por quatro blocos principais:

## 🏗️ **Arquitetura Principal**

### 1. **Core** - Núcleo da Plataforma
- **Autenticação**: JWT minimalista + refresh tokens opacos
- **Usuários**: Gestão de perfis, preferências e permissões
- **Eventos**: Sistema de eventos para comunicação entre componentes
- **Configuração**: Settings centralizados e carregamento automático de módulos

### 2. **Agentes IA** - Núcleo da Inovação
- **Conversação**: Chat natural com agentes especializados
- **Geração de Código**: Código Python, JavaScript, etc. baseado em prompts
- **Revisão de Código**: Análise automática e sugestões de melhoria
- **Debug Assistido**: Identificação e correção de problemas
- **Testes Automáticos**: Geração de testes unitários e de integração

### 3. **Workspace** - Ambiente de Trabalho
- **Gestão de Projetos**: Estrutura de arquivos e diretórios
- **Operações de Código**: Leitura, escrita, edição de arquivos
- **Execução Segura**: Sandbox para código gerado pelos agentes
- **Versionamento**: Controle de versões e histórico de mudanças

### 4. **Integração IA** - OpenAI
- **Modelos Especializados**: GPT-4 para diferentes tipos de agentes
- **Contexto Inteligente**: Agentes entendem o projeto atual
- **Prompts Otimizados**: System prompts específicos para cada agente

## 🔄 **Fluxos Principais**

### **Autenticação e Sessão**
- **Login**: Usuário autentica via `/v1/auth/login`
- **Refresh**: Tokens renovados automaticamente via `/v1/auth/refresh`
- **Sessões**: Gerenciamento de sessões de chat com agentes

### **Conversação com Agentes**
- **Seleção**: Usuário escolhe tipo de agente (gerador, revisor, debug, etc.)
- **Chat**: Conversação natural via `/v1/agents/chat`
- **Contexto**: Agentes acessam arquivos do workspace
- **Ações**: Geração, edição e execução de código

### **Geração e Execução de Código**
- **Prompt**: Usuário descreve o que quer
- **Geração**: Agente gera código usando OpenAI
- **Revisão**: Código é analisado e otimizado
- **Execução**: Código é executado em sandbox seguro
- **Integração**: Código aprovado é salvo no workspace

## 🎯 **Tipos de Agentes Disponíveis**

| Agente | Função | Capacidades |
|--------|--------|-------------|
| **Gerador de Código** | Cria código novo | Leitura, escrita, análise, sugestões |
| **Revisor de Código** | Analisa código existente | Leitura, análise, sugestões de melhoria |
| **Gerador de Testes** | Cria testes automáticos | Leitura, escrita, geração de testes |
| **Assistente de Debug** | Ajuda a resolver problemas | Análise, identificação de bugs, correções |

## 🔒 **Segurança e Limites**

- **Tokens Minimalistas**: Sem PII, apenas identificadores essenciais
- **Sandbox Seguro**: Execução de código isolada e controlada
- **Rate Limiting**: Proteção contra abuso de recursos
- **Auditoria**: Logs completos de todas as operações
- **Permissões**: Controle granular de acesso por usuário/agente

## 🚀 **Visão de Futuro**

A plataforma evolui para ser um **assistente de desenvolvimento completo** onde:
- Desenvolvedores conversam naturalmente com agentes IA
- Código é gerado, revisado e otimizado automaticamente
- Testes são criados e executados automaticamente
- Debugging é assistido por IA especializada
- Documentação é gerada automaticamente
