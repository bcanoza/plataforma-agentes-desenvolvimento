#!/bin/bash
# Script completo para criar infraestrutura Docker em /home/docker
# Execute: cd /home/docker && bash SETUP_INFRA_COMPLETE.sh

echo "🏗️ Configurando Infraestrutura Docker Completa"
echo "==============================================="

# Verificar localização
echo "📍 Localização atual: $(pwd)"
echo "📁 Conteúdo atual:"
ls -la

echo ""
read -p "Criar infraestrutura aqui? [y/N]: " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Operação cancelada"
    exit 0
fi

echo ""
echo "📁 Criando estrutura de diretórios..."
mkdir -p infra/{base,email,apps/assistente,scripts}
mkdir -p infra/{base,email,apps/assistente}/config

echo "📄 Criando arquivos de configuração..."

# 1. Infraestrutura Base
cat > infra/base/docker-compose.yml << 'EOF'
version: '3.8'

services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: always
    networks:
      - web
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/traefik.toml:/traefik.toml:ro
      - ./config/acme.json:/acme.json
    environment:
      - TZ=America/Sao_Paulo
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    ports:
      - "9000:9000"
      - "9443:9443"
    networks:
      - web
    environment:
      - TZ=America/Sao_Paulo
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.portainer.rule=Host(\`portainer.odontoapi.com\`)"
      - "traefik.http.routers.portainer.tls=true"
      - "traefik.http.services.portainer.loadbalancer.server.port=9000"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  portainer_data:

networks:
  web:
    external: true
EOF

# 2. Aplicação Assistente
cat > infra/apps/assistente/docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: assistente_postgres
    restart: always
    environment:
      POSTGRES_DB: assistente
      POSTGRES_USER: app_writer
      POSTGRES_PASSWORD: ${DB_PASS:-password}
      TZ: America/Sao_Paulo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - assistente_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app_writer -d assistente"]
      interval: 30s
      timeout: 10s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: assistente_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - assistente_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  api:
    build: 
      context: ../../../app
      dockerfile: Dockerfile
    container_name: assistente_api
    restart: always
    ports:
      - "7000:7000"
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=${DB_PASS:-password}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
      - INTERNAL_API_BASE=http://api:7000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - assistente_network
      - web
    volumes:
      - ../../../app:/app
      - api_logs:/app/logs
    command: uvicorn app.main:app --host 0.0.0.0 --port 7000 --reload
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.assistente-api.rule=Host(\`api.odontoapi.com\`)"
      - "traefik.http.routers.assistente-api.tls=true"
      - "traefik.http.services.assistente-api.loadbalancer.server.port=7000"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  worker:
    build: 
      context: ../../../app
      dockerfile: Dockerfile
    container_name: assistente_worker
    restart: always
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=${DB_PASS:-password}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - assistente_network
    volumes:
      - ../../../app:/app
      - worker_logs:/app/logs
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  beat:
    build: 
      context: ../../../app
      dockerfile: Dockerfile
    container_name: assistente_beat
    restart: always
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=${DB_PASS:-password}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - assistente_network
    volumes:
      - ../../../app:/app
      - beat_logs:/app/logs
    command: celery -A app.core.celery_app beat --loglevel=info
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  flower:
    build: 
      context: ../../../app
      dockerfile: Dockerfile
    container_name: assistente_flower
    restart: always
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
    ports:
      - "5555:5555"
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - assistente_network
      - web
    command: celery -A app.core.celery_app flower --port=5555
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.assistente-flower.rule=Host(\`flower.odontoapi.com\`)"
      - "traefik.http.routers.assistente-flower.tls=true"
      - "traefik.http.services.assistente-flower.loadbalancer.server.port=5555"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
  redis_data:
  api_logs:
  worker_logs:
  beat_logs:

networks:
  assistente_network:
    driver: bridge
    name: assistente_network
  web:
    external: true
EOF

# 3. .env.example para aplicação
cat > infra/apps/assistente/.env.example << 'EOF'
# Configurações da Aplicação Assistente
DB_PASS=sua_senha_postgres_segura
OPENAI_API_KEY=sk-sua_chave_openai_aqui
APP_SECRET=sua_chave_jwt_secreta

# Opcionais (já têm padrões)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=assistente
DB_USER=app_writer
REDIS_URL=redis://redis:6379/0
TZ=America/Sao_Paulo
CORS_ORIGINS=https://odontoapi.com
LOG_LEVEL=INFO
EOF

# 4. Script de gerenciamento
cat > infra/scripts/manage.sh << 'EOF'
#!/bin/bash
echo "🎮 Gerenciador da Infraestrutura Assistente"
echo "==========================================="
echo ""
echo "1) deploy-all      - Deploy completo" 
echo "2) deploy-app      - Deploy só aplicação"
echo "3) stop-all        - Parar tudo"
echo "4) status          - Ver status"
echo "5) logs-api        - Logs da API"
echo "6) logs-worker     - Logs do Worker"
echo "7) restart-app     - Reiniciar aplicação"
echo "0) Sair"
echo ""
read -p "Escolha [0-7]: " choice

cd "$(dirname "$0")"

case $choice in
    1) 
        echo "🚀 Deploy completo..."
        cd ../base && docker-compose up -d
        cd ../apps/assistente && docker-compose up -d
        echo "✅ Deploy concluído!"
        ;;
    2)
        echo "📱 Deploy aplicação..."
        cd ../apps/assistente && docker-compose up -d
        echo "✅ Aplicação deployada!"
        ;;
    3)
        echo "🛑 Parando serviços..."
        cd ../apps/assistente && docker-compose down
        cd ../base && docker-compose down
        echo "✅ Serviços parados!"
        ;;
    4)
        echo "📊 Status dos serviços:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    5)
        echo "📋 Logs da API:"
        docker logs -f assistente_api
        ;;
    6) 
        echo "📋 Logs do Worker:"
        docker logs -f assistente_worker
        ;;
    7)
        echo "🔄 Reiniciando aplicação..."
        cd ../apps/assistente
        docker-compose restart
        echo "✅ Aplicação reiniciada!"
        ;;
    0) 
        echo "👋 Até logo!"
        exit 0
        ;;
    *)
        echo "❌ Opção inválida!"
        ;;
esac
EOF

chmod +x infra/scripts/manage.sh

# 5. Dockerfile (se não existir)
if [ ! -f "app/Dockerfile" ]; then
    mkdir -p app
    cat > app/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar flower
RUN pip install --no-cache-dir flower

COPY . .

RUN mkdir -p /app/logs

EXPOSE 7000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7000"]
EOF
fi

# 6. Docker-compose simples na raiz (compatibilidade)
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: assistente_postgres
    restart: always
    environment:
      POSTGRES_DB: assistente
      POSTGRES_USER: app_writer
      POSTGRES_PASSWORD: password
      TZ: America/Sao_Paulo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - assistente_network

  redis:
    image: redis:7-alpine
    container_name: assistente_redis
    restart: always
    ports:
      - "6379:6379"
    networks:
      - assistente_network

  api:
    build: ./app
    container_name: assistente_api
    restart: always
    ports:
      - "7000:7000"
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=password
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
      - INTERNAL_API_BASE=http://api:7000
    depends_on:
      - postgres
      - redis
    networks:
      - assistente_network
    volumes:
      - ./app:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 7000 --reload

  worker:
    build: ./app
    container_name: assistente_worker
    restart: always
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=password
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
    depends_on:
      - postgres
      - redis
    networks:
      - assistente_network
    volumes:
      - ./app:/app
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4

  beat:
    build: ./app
    container_name: assistente_beat
    restart: always
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=assistente
      - DB_USER=app_writer
      - DB_PASS=password
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
    depends_on:
      - postgres
      - redis
    networks:
      - assistente_network
    volumes:
      - ./app:/app
    command: celery -A app.core.celery_app beat --loglevel=info

  flower:
    build: ./app
    container_name: assistente_flower
    restart: always
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - TZ=America/Sao_Paulo
    ports:
      - "5555:5555"
    depends_on:
      - redis
    networks:
      - assistente_network
    command: celery -A app.core.celery_app flower --port=5555

volumes:
  postgres_data:
  redis_data:

networks:
  assistente_network:
    driver: bridge
EOF

# 7. Configuração Redis
cat > infra/apps/assistente/config/redis.conf << 'EOF'
# Configuração Redis para Assistente
save 900 1
save 300 10
save 60 10000
protected-mode yes
port 6379
maxmemory 512mb
maxmemory-policy allkeys-lru
loglevel notice
databases 16
tcp-backlog 511
EOF

echo ""
echo "🎉 Infraestrutura criada com sucesso!"
echo ""
echo "📍 Estrutura criada:"
find infra/ -type f | sort

echo ""
echo "🚀 Próximos passos:"
echo ""
echo "1. Configurar ambiente (se necessário):"
echo "   cd infra/apps/assistente"
echo "   cp .env.example .env"
echo "   nano .env  # Editar configurações"
echo ""
echo "2. Criar network externa:"
echo "   docker network create web"
echo ""
echo "3. Iniciar aplicação:"
echo "   # Opção A - Versão simples"
echo "   docker-compose up -d"
echo ""
echo "   # Opção B - Versão modular"
echo "   cd infra/scripts && ./manage.sh"
echo ""
echo "4. Verificar status:"
echo "   docker ps"
echo ""
echo "🌐 URLs importantes:"
echo "  • API: http://localhost:7000"
echo "  • Flower: http://localhost:5555"
echo "  • Portainer: http://localhost:9000"
echo ""
echo "✅ Sua infraestrutura Docker está pronta!"
EOF

chmod +x SETUP_INFRA_COMPLETE.sh

echo "🎯 Script criado: SETUP_INFRA_COMPLETE.sh"
echo ""
echo "Para usar no /home/docker, execute:"
echo ""
echo "curl -o SETUP_INFRA_COMPLETE.sh https://raw.githubusercontent.com/[este_arquivo]"
echo "# OU copie o conteúdo do script e cole num arquivo"
echo ""
echo "cd /home/docker"
echo "bash SETUP_INFRA_COMPLETE.sh"