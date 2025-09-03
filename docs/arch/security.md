# Arquitetura – Segurança

## 🔒 **Visão Geral de Segurança**

A plataforma de agentes de desenvolvimento implementa múltiplas camadas de segurança para proteger tanto os dados dos usuários quanto a infraestrutura de execução de código.

## 🎫 **Autenticação e Autorização**

### **Tokens JWT Minimalistas**
- **Estrutura**: `accessToken` com `iss,aud,sub,iat,exp,jti,sid,ver,roles[,amr,auth_time]`
- **Sem PII**: Tokens não carregam informações pessoais identificáveis
- **Sem Preferências**: Configurações carregadas separadamente via `/v1/users/me`
- **Rotação**: Refresh tokens opacos rotacionados a cada `/auth/refresh`

### **Sistema de Permissões**
- **Usuários**: Acesso aos próprios recursos e projetos
- **Admins**: Acesso administrativo e gestão de usuários
- **Agentes**: Acesso controlado ao workspace baseado em contexto

### **Refresh Tokens Seguros**
- **Armazenamento**: Tokens opacos mantidos no servidor
- **Rotação Obrigatória**: Novo token a cada refresh
- **Invalidação**: Logout invalida todos os tokens do usuário
- **Expiração**: Timeout configurável para inatividade

## 🌐 **Proteção de Rede**

### **CORS (Cross-Origin Resource Sharing)**
- **Origens Restritas**: Apenas domínios confiáveis autorizados
- **Headers Limitados**: Apenas headers necessários permitidos
- **Métodos Controlados**: GET, POST, PUT, DELETE, OPTIONS
- **Credentials**: Cookies e headers de autenticação controlados

### **CSRF (Cross-Site Request Forgery)**
- **SameSite Cookies**: Proteção contra ataques CSRF
- **Double-Submit Token**: Token adicional para operações críticas
- **Referer Validation**: Verificação de origem das requisições
- **State Validation**: Validação de estado em operações sensíveis

## 🚦 **Rate Limiting e Anti-Brute Force**

### **Limites por Usuário**
- **Chat com Agentes**: 100 mensagens/hora por usuário
- **Geração de Código**: 50 requisições/hora por usuário
- **Execução de Código**: 20 execuções/hora por usuário
- **Upload de Arquivos**: 10MB/hora por usuário

### **Limites por IP**
- **Login**: 5 tentativas por minuto por IP
- **API Geral**: 1000 requisições/hora por IP
- **Endpoints Críticos**: 100 requisições/hora por IP

### **Proteção Anti-Brute Force**
- **Bloqueio Temporário**: 15 minutos após 5 tentativas falhas
- **Bloqueio Progressivo**: Aumento exponencial do tempo de bloqueio
- **Whitelist**: IPs confiáveis podem ter limites relaxados
- **Monitoramento**: Alertas para tentativas suspeitas

## 🏃‍♂️ **Sandbox de Execução**

### **Isolamento de Código**
- **Container Isolation**: Código executado em containers isolados
- **Resource Limits**: CPU, memória e tempo limitados
- **Network Isolation**: Sem acesso à rede externa por padrão
- **Filesystem Isolation**: Acesso restrito ao workspace do usuário

### **Controle de Recursos**
- **CPU**: Máximo 1 core por execução
- **Memória**: Máximo 512MB por execução
- **Tempo**: Máximo 30 segundos por execução
- **Arquivos**: Máximo 10MB de arquivos temporários

### **Operações Bloqueadas**
- **Sistema**: Acesso a `/proc`, `/sys`, `/dev`
- **Rede**: Conexões externas não autorizadas
- **Arquivos**: Escrita fora do workspace
- **Processos**: Criação de processos filhos
- **Bibliotecas**: Importação de módulos perigosos

## 📝 **Auditoria e Logs**

### **Logs de Segurança**
- **Autenticação**: Tentativas de login (sucesso/falha)
- **Autorização**: Acessos negados e tentativas de escalação
- **Execução**: Código executado e recursos utilizados
- **Agentes**: Interações com agentes IA

### **Tratamento de Dados Sensíveis**
- **Tokens**: Nunca logados completos, apenas prefixos
- **Senhas**: Nunca logadas, apenas hash
- **Código**: Logado apenas metadados, não conteúdo
- **PII**: Dados pessoais mascarados ou omitidos

### **Correlação de Eventos**
- **Trace ID**: Identificador único para rastrear requisições
- **Session ID**: Correlação de atividades por sessão
- **User ID**: Rastreamento de atividades por usuário
- **Timestamp**: Marcação temporal precisa

## 🔑 **Gestão de Chaves**

### **JWKS (JSON Web Key Set)**
- **Publicação**: Chaves públicas disponíveis em `/.well-known/jwks.json`
- **Rotação**: Chaves rotacionadas regularmente
- **Kid Header**: Identificador de chave nos tokens JWT
- **Algoritmo**: RS256 para assinatura digital

### **API Keys**
- **Geração**: Chaves únicas para integrações externas
- **Escopo**: Permissões limitadas por chave
- **Rotação**: Renovação periódica obrigatória
- **Revogação**: Invalidação imediata quando necessário

## 🛡️ **Proteção de Dados**

### **Criptografia**
- **Em Trânsito**: TLS 1.3 para todas as comunicações
- **Em Repouso**: AES-256 para dados sensíveis
- **Senhas**: bcrypt com salt único
- **Tokens**: Assinatura digital RS256

### **Backup e Recuperação**
- **Backup Automático**: Diário com retenção de 30 dias
- **Criptografia**: Backups criptografados
- **Teste de Restore**: Validação mensal de backups
- **Disaster Recovery**: Plano de recuperação documentado

## 🔍 **Monitoramento de Segurança**

### **Métricas de Segurança**
- **Tentativas de Login**: Sucesso/falha por hora
- **Rate Limiting**: Bloqueios por IP/usuário
- **Execuções**: Código executado e recursos
- **Erros**: Falhas de autenticação/autorização

### **Alertas Automáticos**
- **Múltiplas Falhas**: 10+ tentativas de login falhas
- **Uso Anômalo**: Padrões suspeitos de uso
- **Recursos**: Uso excessivo de CPU/memória
- **Erros**: Falhas críticas de segurança

### **Análise de Comportamento**
- **Padrões de Uso**: Detecção de uso anômalo
- **Geolocalização**: Tentativas de acesso de locais suspeitos
- **Horários**: Acesso em horários não usuais
- **Dispositivos**: Mudanças de dispositivo/browser

## 🚨 **Resposta a Incidentes**

### **Classificação de Incidentes**
- **Crítico**: Comprometimento de dados ou sistema
- **Alto**: Tentativas de acesso não autorizado
- **Médio**: Uso anômalo ou suspeito
- **Baixo**: Violações menores de política

### **Procedimentos de Resposta**
- **Detecção**: Monitoramento automático e manual
- **Contenção**: Isolamento de sistemas afetados
- **Investigação**: Análise forense e coleta de evidências
- **Recuperação**: Restauração de serviços e dados
- **Lições Aprendidas**: Documentação e melhorias

## 📋 **Compliance e Regulamentação**

### **LGPD (Lei Geral de Proteção de Dados)**
- **Consentimento**: Consentimento explícito para coleta de dados
- **Minimização**: Coleta apenas de dados necessários
- **Transparência**: Política de privacidade clara
- **Direitos**: Acesso, correção e exclusão de dados

### **Boas Práticas**
- **Princípio do Menor Privilégio**: Acesso mínimo necessário
- **Defesa em Profundidade**: Múltiplas camadas de segurança
- **Segurança por Design**: Segurança integrada desde o início
- **Atualizações**: Manutenção regular de dependências

## 🔄 **Revisão e Atualização**

### **Revisões Periódicas**
- **Mensal**: Revisão de logs e métricas de segurança
- **Trimestral**: Auditoria de permissões e acessos
- **Semestral**: Teste de penetração e vulnerabilidades
- **Anual**: Revisão completa da arquitetura de segurança

### **Atualizações de Segurança**
- **Dependências**: Atualização regular de bibliotecas
- **Sistema**: Patches de segurança do sistema operacional
- **Configurações**: Revisão e atualização de configurações
- **Treinamento**: Capacitação da equipe em segurança
