# 🔄 Guia de Migração - Infraestrutura Docker

## 📋 **Situação Atual vs Nova Estrutura**

### **❌ Antes (Estrutura Original)**
```
/
├── docker-compose.yml (traefik + portainer + TUDO misturado)
├── email/
│   └── docker-compose.yml (servidor email)
└── app/ (aplicação sem docker adequado)
```

### **✅ Agora (Estrutura Modular)**
```
infra/
├── base/                 # Infraestrutura base
│   └── docker-compose.yml
├── email/                # Servidor email organizado  
│   ├── docker-compose.yml
│   └── config/
├── apps/assistente/      # Aplicação isolada
│   ├── docker-compose.yml
│   ├── .env.example
│   └── config/
└── scripts/              # Automação completa
    ├── manage.sh (🎮 PRINCIPAL)
    ├── deploy.sh
    ├── stop.sh
    ├── monitor.sh
    ├── backup.sh
    └── logs.sh
```

## 🚀 **Processo de Migração**

### **Passo 1: Preparar Ambiente**
```bash
# 1. Parar setup atual (com cuidado!)
docker-compose down

# 2. Fazer backup dos dados atuais
docker run --rm -v $(docker volume ls -q | grep postgres):/backup-source \
  -v $(pwd)/backup_migration:/backup alpine \
  tar czf /backup/postgres_data.tar.gz -C /backup-source .

# 3. Backup configs existentes
cp docker-compose.yml docker-compose.yml.backup
cp -r email/ email_backup/
```

### **Passo 2: Configurar Nova Estrutura**
```bash
# 1. Configurar aplicação
cd infra/apps/assistente
cp .env.example .env

# 2. Editar variáveis importantes
nano .env
# - DB_PASS=sua_senha_postgres
# - OPENAI_API_KEY=sua_chave
# - APP_SECRET=sua_chave_jwt

# 3. Migrar configurações do email (se houver)
# cp ../../../email_backup/config/* ../email/config/
```

### **Passo 3: Deploy Gradual**
```bash
# 1. Usar o gerenciador principal
cd infra/scripts
./manage.sh

# OU fazer manualmente:

# 2. Deploy base primeiro
./deploy.sh

# 3. Verificar se base está ok
./monitor.sh

# 4. Deploy aplicação
cd ../apps/assistente
docker-compose up -d

# 5. Verificar tudo
cd ../../scripts
./monitor.sh
```

## ⚠️ **Pontos de Atenção na Migração**

### **1. Dados Existentes**
- **PostgreSQL**: Os dados serão preservados se usar volumes nomeados
- **Redis**: Dados em cache podem ser perdidos (normal)
- **Logs**: Configurar volumes para preservar histórico

### **2. Networks**
- A network `web` deve existir: `docker network create web`
- Novos networks serão criados automaticamente

### **3. Domínios e SSL**
- Verificar se certificados SSL existem em `/home/docker/traefik/`
- Atualizar configurações de domínio se necessário

### **4. Ports**
- **7000**: API Principal (mudou de 8000?)
- **5555**: Flower
- **5432**: PostgreSQL
- **6379**: Redis

## 🔧 **Verificações Pós-Migração**

### **1. Conectividade**
```bash
# API respondendo
curl http://localhost:7000/

# PostgreSQL conectando
docker exec assistente_postgres psql -U app_writer -d assistente -c "SELECT version();"

# Redis funcionando
docker exec assistente_redis redis-cli ping

# Celery worker ativo
docker exec assistente_worker celery -A app.core.celery_app inspect active
```

### **2. Monitoramento**
- **Flower**: http://localhost:5555
- **Portainer**: http://localhost:9000
- **API Docs**: http://localhost:7000/docs

### **3. Logs**
```bash
cd infra/scripts

# Verificar logs da API
./logs.sh api -n 50

# Verificar logs do worker
./logs.sh worker -n 50

# Monitor geral
./monitor.sh
```

## 🎯 **Comandos Essenciais da Nova Estrutura**

### **Uso Diário**
```bash
# Gerenciador interativo (RECOMENDADO)
cd infra/scripts && ./manage.sh

# Deploy rápido da aplicação
cd infra/apps/assistente && docker-compose up -d

# Status rápido
cd infra/scripts && ./monitor.sh

# Logs em tempo real
cd infra/scripts && ./logs.sh api -f
```

### **Manutenção**
```bash
# Backup completo
cd infra/scripts && ./backup.sh

# Restart da aplicação
cd infra/apps/assistente && docker-compose restart

# Escalar workers
cd infra/apps/assistente && docker-compose up -d --scale worker=3
```

## 🆘 **Rollback de Emergência**

Se algo der errado, você pode voltar para o setup anterior:

```bash
# 1. Parar nova estrutura
cd infra/scripts && ./stop.sh

# 2. Restaurar docker-compose antigo
cp docker-compose.yml.backup docker-compose.yml

# 3. Restaurar dados (se necessário)
# Restaurar volumes de backup...

# 4. Subir setup antigo
docker-compose up -d
```

## 🎉 **Benefícios da Nova Estrutura**

✅ **Organização**: Cada serviço tem seu lugar  
✅ **Manutenção**: Scripts automatizados para tudo  
✅ **Escalabilidade**: Fácil adicionar novos serviços  
✅ **Monitoramento**: Visibilidade completa  
✅ **Backup**: Estratégia robusta e automatizada  
✅ **Deploy**: Independente por camada  
✅ **Debugging**: Logs organizados e acessíveis  

---

**Data**: $(date)  
**Responsável**: Sistema de Agentes IA  
**Status**: Pronto para produção