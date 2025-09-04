#!/bin/bash
# Script para parar todos os serviços da infraestrutura
set -e

echo "🛑 Parando infraestrutura..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

stop_service() {
    local service_path=$1
    local service_name=$2
    
    if [ -d "$service_path" ]; then
        log "⏹️ Parando: $service_name"
        cd "$service_path"
        docker-compose down
        cd - >/dev/null
    else
        warn "Diretório não encontrado: $service_path"
    fi
}

# Parar na ordem reversa (aplicação primeiro, infraestrutura por último)

# 1. Parar aplicação assistente
stop_service "../apps/assistente" "Aplicação Assistente"

# 2. Parar servidor de email
stop_service "../email" "Servidor de Email"

# 3. Parar infraestrutura base
if [ "$1" != "--keep-base" ]; then
    stop_service "../base" "Infraestrutura Base"
else
    warn "Mantendo infraestrutura base (Traefik/Portainer) rodando"
fi

log "🎉 Todos os serviços foram parados!"

# Mostrar containers restantes
echo ""
echo "🐳 Containers ainda rodando:"
docker ps --format "table {{.Names}}\t{{.Status}}"