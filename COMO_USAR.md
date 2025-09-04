# 🚀 Como Usar a Infraestrutura (Criada na Raiz do Projeto)

## 📍 **Localização**
A infraestrutura está **aqui na raiz do projeto** onde você já está!

```
./ (raiz do projeto)
├── infra/                        ← 🏗️ Infraestrutura organizada AQUI
│   ├── apps/assistente/          ← 📱 Sua aplicação principal
│   │   └── docker-compose.yml    #   (PostgreSQL + Redis + API + Worker + Beat + Flower)
│   ├── base/                     ← 🏗️ Infraestrutura base  
│   │   └── docker-compose.yml    #   (Traefik + Portainer)
│   └── scripts/                  ← 🤖 Scripts de automação
│       ├── manage.sh             #   🎮 GERENCIADOR PRINCIPAL
│       ├── deploy.sh             #   🚀 Deploy automático  
│       ├── monitor.sh            #   📊 Status dos serviços
│       └── outros...
├── app/                          ← 👨‍💻 Código da aplicação (já existia)
├── docker-compose.yml           ← ⚡ Versão simples (reconstruída)
└── docs/                        ← 📚 Documentação (já existia)
```

---

## ⚡ **USAR IMEDIATAMENTE (3 opções):**

### **Opção 1: Gerenciador Interativo (RECOMENDADO)**
```bash
# Usar menu interativo com todas as opções
cd infra/scripts
./manage.sh
```

### **Opção 2: Deploy Direto** 
```bash
# Deploy automático completo
cd infra/scripts  
./deploy.sh all
```

### **Opção 3: Docker-Compose Simples**
```bash
# Usar versão simplificada na raiz
docker-compose up -d
```

---

## 🔧 **Configuração (se necessário):**

### **1. Configurar variáveis de ambiente:**
```bash
cd infra/apps/assistente
cp .env.example .env
nano .env  # Editar suas configurações
```

### **2. Criar network (uma vez só):**
```bash
docker network create web
```

---

## 📊 **Comandos Úteis:**

```bash
# Ver status de tudo
cd infra/scripts && ./monitor.sh

# Ver logs da API
./logs.sh api -f

# Ver logs do Worker
./logs.sh worker -f

# Parar tudo
./stop.sh

# Backup completo
./backup.sh
```

---

## 🌐 **Acessos Depois de Iniciar:**

- **🌐 API Principal**: http://localhost:7000
- **🌺 Flower (Monitor Celery)**: http://localhost:5555  
- **🐳 Portainer**: http://localhost:9000
- **📱 API Docs**: http://localhost:7000/docs

---

## 🎯 **Resumo:**
✅ **Infraestrutura já criada AQUI na raiz do projeto**  
✅ **Todos os serviços configurados** (PostgreSQL, Redis, API, Worker, Beat, Flower)  
✅ **Scripts de automação prontos**  
✅ **Docker-compose reconstruído**  

**Pronto para usar agora mesmo!** 🚀

Execute: `cd infra/scripts && ./manage.sh`