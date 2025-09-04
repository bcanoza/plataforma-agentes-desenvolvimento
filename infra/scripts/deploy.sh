#!/bin/bash
# Script para deploy da infraestrutura completa
set -e

echo "🚀 Iniciando deploy da infraestrutura..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Verificar se Docker está rodando
if ! docker info >/dev/null 2>&1; then
    error "Docker não está rodando! Inicie o Docker primeiro."
    exit 1
fi

# Criar network externa se não existir
if ! docker network ls | grep -q "web"; then
    log "Criando network externa 'web'..."
    docker network create web
fi

# Deploy por ordem de dependência
deploy_service() {
    local service_path=$1
    local service_name=$2
    
    log "📦 Iniciando deploy: $service_name"
    cd "$service_path"
    
    # Verificar se existe .env local
    if [ -f ".env" ]; then
        log "Usando configurações .env local"
    else
        warn "Arquivo .env não encontrado em $service_path"
    fi
    
    # Build e up
    docker-compose pull
    docker-compose build --no-cache
    docker-compose up -d
    
    log "✅ $service_name deployado com sucesso"
    cd - >/dev/null
}

# 1. Deploy da infraestrutura base
deploy_service "../base" "Infraestrutura Base (Traefik + Portainer)"

# Aguardar Traefik estar pronto
log "⏳ Aguardando Traefik estar pronto..."
sleep 10

# 2. Deploy do servidor de email (opcional)
if [ "$1" == "email" ] || [ "$1" == "all" ]; then
    deploy_service "../email" "Servidor de Email"
fi

# 3. Deploy da aplicação assistente
deploy_service "../apps/assistente" "Aplicação Assistente"

# Verificar saúde dos serviços
log "🔍 Verificando saúde dos serviços..."
sleep 15

# Status final
echo ""
echo "📊 Status dos serviços:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
log "🎉 Deploy concluído com sucesso!"
echo ""
echo "📡 Acessos:"
echo "  • API Assistente: http://localhost:7000"
echo "  • Flower (Celery): http://localhost:5555"
echo "  • Portainer: http://localhost:9000"
echo "  • Traefik Dashboard: http://localhost:8080"

if [ "$1" == "email" ] || [ "$1" == "all" ]; then
    echo "  • Webmail: https://webmail.odontoapi.com"
fi