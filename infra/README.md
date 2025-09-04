# 🏗️ Infraestrutura Docker - Assistente

Estrutura modular para gerenciar a infraestrutura completa da aplicação Assistente usando Docker Compose.

## 📁 **Estrutura Organizacional**

```
infra/
├── base/                 # Infraestrutura base (Traefik + Portainer)
│   └── docker-compose.yml
├── email/                # Servidor de email
│   ├── docker-compose.yml
│   └── config/
├── apps/
│   └── assistente/       # Aplicação principal
│       ├── docker-compose.yml
│       ├── .env.example
│       └── config/
└── scripts/              # Scripts de gerenciamento
    ├── deploy.sh
    ├── stop.sh
    ├── monitor.sh
    ├── backup.sh
    └── logs.sh
```

## 🎯 **Filosofia de Organização**

### **Separação por Responsabilidade**
- **Base**: Serviços de infraestrutura comum (proxy, monitoramento)
- **Email**: Serviços de comunicação isolados
- **Apps**: Aplicações de negócio específicas
- **Scripts**: Automação e operações

### **Vantagens desta Estrutura**
✅ **Deploy Independente** - Cada camada pode ser atualizada separadamente  
✅ **Isolamento** - Falha em um serviço não afeta outros  
✅ **Escalabilidade** - Fácil adicionar novas aplicações  
✅ **Manutenção** - Configurações organizadas e localizadas  
✅ **Backup/Restore** - Estratégias específicas por serviço  
✅ **Debugging** - Logs e monitoramento centralizados  

## 🚀 **Guia de Uso**

### **Inicialização Completa**
```bash
# Navegar para scripts
cd infra/scripts

# Deploy completo (base + aplicação)
./deploy.sh all

# Deploy apenas aplicação (se base já estiver rodando)
./deploy.sh
```

### **Operações Específicas**

#### **Deploy por Camadas**
```bash
# Apenas infraestrutura base
cd infra/base && docker-compose up -d

# Apenas aplicação assistente
cd infra/apps/assistente && docker-compose up -d

# Apenas servidor de email
cd infra/email && docker-compose up -d
```

#### **Monitoramento**
```bash
# Status geral
cd infra/scripts && ./monitor.sh

# Logs específicos
./logs.sh api -f          # Logs da API em tempo real
./logs.sh worker -n 100   # Últimas 100 linhas do worker
./logs.sh all             # Logs de todos os serviços
```

#### **Backup e Restore**
```bash
# Backup completo
cd infra/scripts && ./backup.sh

# Parar tudo
./stop.sh

# Parar mantendo base (Traefik/Portainer)
./stop.sh --keep-base
```

## 🔧 **Configuração**

### **1. Configurar Ambiente**
```bash
# Aplicação principal
cd infra/apps/assistente
cp .env.example .env
# Edite .env com suas configurações

# Configurar outros serviços conforme necessário
```

### **2. Variáveis Importantes**
```bash
# Banco de dados
DB_PASS=sua_senha_postgres

# OpenAI
OPENAI_API_KEY=sua_chave_openai

# Segurança
APP_SECRET=sua_chave_jwt_secreta

# Domínios
CORS_ORIGINS=https://seudominio.com
COOKIE_DOMAIN=.seudominio.com
```

## 🌐 **Networks e Conectividade**

### **Networks Configuradas**
- **`web`** (externa) - Para Traefik e serviços expostos
- **`assistente_network`** - Comunicação interna da aplicação
- **`email_network`** - Comunicação do sistema de email

### **Portas Expostas**
- **7000** - API Principal
- **5555** - Flower (Celery Monitor)
- **5432** - PostgreSQL
- **6379** - Redis
- **80/443** - Traefik (HTTP/HTTPS)
- **9000** - Portainer
- **25/587/993** - Email (SMTP/IMAP)

## 🔄 **Serviços da Aplicação Assistente**

| Serviço | Container | Função | Dependências |
|---------|-----------|---------|--------------|
| **API** | `assistente_api` | FastAPI REST API | postgres, redis |
| **Worker** | `assistente_worker` | Celery worker | postgres, redis |
| **Beat** | `assistente_beat` | Agendador Celery | postgres, redis |
| **Flower** | `assistente_flower` | Monitor Celery | redis |
| **PostgreSQL** | `assistente_postgres` | Banco principal | - |
| **Redis** | `assistente_redis` | Cache/Broker | - |

## 🛡️ **Segurança e Boas Práticas**

### **Health Checks**
- Todos os serviços têm verificações de saúde
- Dependências aguardam serviços estarem prontos
- Restart automático em caso de falha

### **Logs Estruturados**
- Rotação automática (10MB, 3 arquivos)
- Timestamps consistentes
- Formato JSON para parsing

### **Volumes Persistentes**
- Dados do PostgreSQL preservados
- Configurações externalizadas
- Logs organizados por serviço

## 🔧 **Comandos Úteis**

```bash
# Status rápido
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs em tempo real
docker-compose logs -f api worker

# Reiniciar um serviço específico
docker-compose restart api

# Escalar workers
docker-compose up -d --scale worker=3

# Backup manual do banco
docker exec assistente_postgres pg_dump -U app_writer assistente > backup_$(date +%Y%m%d).sql
```

## 📋 **Troubleshooting**

### **Problemas Comuns**

1. **Network não existe**
   ```bash
   docker network create web
   ```

2. **Porta já em uso**
   ```bash
   # Verificar o que está usando a porta
   netstat -tulpn | grep :5432
   ```

3. **Containers não iniciam**
   ```bash
   # Verificar logs
   ./scripts/logs.sh postgres
   ```

4. **Problemas de permissão**
   ```bash
   # Ajustar permissões
   sudo chown -R $USER:$USER infra/
   ```

## 🎯 **Próximos Passos Sugeridos**

1. **Monitoramento Avançado** - Adicionar Prometheus + Grafana
2. **CI/CD** - Integrar pipeline de deploy automático
3. **Backup Automático** - Cronjobs para backup regular
4. **Alertas** - Notificações quando serviços falham
5. **Load Balancer** - Múltiplas instâncias da API

---

**Criado em**: $(date)  
**Versão**: 1.0.0