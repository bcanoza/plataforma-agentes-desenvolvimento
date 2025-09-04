# 🏗️ Setup da Infraestrutura Docker

## 📁 Estrutura Criada

```
infra/
├── base/                     # Infraestrutura básica
│   └── docker-compose.yml   # Traefik + Portainer
├── apps/
│   └── assistente/           # Aplicação principal
│       ├── docker-compose.yml  # PostgreSQL + Redis + API + Worker + Beat + Flower
│       ├── .env.example        # Configurações
│       └── config/
│           └── redis.conf      # Config Redis
├── scripts/                  # Automação
│   ├── manage.sh            # 🎮 Gerenciador principal
│   ├── deploy.sh            # 🚀 Deploy automático
│   ├── monitor.sh           # 📊 Monitoramento
│   └── quick.sh             # ⚡ Comandos rápidos
└── docs/
    └── setup.md             # Esta documentação
```

## 🚀 Início Rápido

### Opção 1: Menu Interativo
```bash
cd infra/scripts
./manage.sh
```

### Opção 2: Comandos Rápidos
```bash
cd infra/scripts
./quick.sh start          # Iniciar aplicação
./quick.sh status         # Ver status
./quick.sh full-start     # Iniciar tudo
```

### Opção 3: Deploy Automático
```bash
cd infra/scripts
./deploy.sh 3             # Deploy completo
```

## ⚙️ Configuração

### Configurar Variáveis de Ambiente
```bash
cd infra/apps/assistente
cp .env.example .env
nano .env  # Editar configurações importantes
```

### Variáveis Obrigatórias
```bash
DB_PASS=sua_senha_postgres
OPENAI_API_KEY=sk-sua_chave_openai
APP_SECRET=sua_chave_jwt
```

## 🌐 URLs Depois de Iniciar

- **API Principal**: http://localhost:7000
- **Documentação API**: http://localhost:7000/docs
- **Flower (Celery)**: http://localhost:5555
- **Portainer**: http://localhost:9000

## 📊 Serviços Incluídos

| Serviço | Container | Porta | Função |
|---------|-----------|--------|---------|
| PostgreSQL | assistente_postgres | 5432 | Banco de dados |
| Redis | assistente_redis | 6379 | Cache + Broker |
| API | assistente_api | 7000 | FastAPI REST |
| Worker | assistente_worker | - | Celery Worker |
| Beat | assistente_beat | - | Agendador |
| Flower | assistente_flower | 5555 | Monitor Celery |

## 🛠️ Comandos Úteis

```bash
# Status rápido
docker ps --format "table {{.Names}}\t{{.Status}}"

# Logs específicos
docker logs -f assistente_api
docker logs -f assistente_worker

# Backup manual
docker exec assistente_postgres pg_dump -U app_writer assistente > backup.sql

# Conectar no banco
docker exec -it assistente_postgres psql -U app_writer -d assistente

# Escalar workers
cd infra/apps/assistente
docker-compose up -d --scale worker=3
```