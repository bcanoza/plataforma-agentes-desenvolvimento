# 🏗️ Infraestrutura Docker - Assistente

## 📁 Estrutura Organizada

```
infra/
├── base/                     # Infraestrutura básica
│   └── docker-compose.yml   # Traefik + Portainer
├── apps/
│   └── assistente/           # Aplicação principal
│       ├── docker-compose.yml
│       ├── .env.example
│       └── config/
├── scripts/                  # Automação
│   ├── manage.sh
│   ├── deploy.sh
│   └── monitor.sh
└── docs/                     # Documentação
    └── setup.md
```

## 🚀 Uso Rápido

```bash
# Deploy da aplicação
cd infra/apps/assistente
docker-compose up -d

# OU usar scripts de automação
cd infra/scripts  
./manage.sh
```

## 🌐 Serviços

- **PostgreSQL**: porta 5432
- **Redis**: porta 6379
- **API**: porta 7000
- **Flower**: porta 5555