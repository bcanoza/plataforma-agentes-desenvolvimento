#!/bin/bash
# Script de deploy para aplicação Assistente

echo "🚀 Deploy da Aplicação Assistente"
echo "================================="

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m' 
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado!"
    exit 1
fi

# Criar network se necessário
if ! docker network ls | grep -q "web"; then
    log "🌐 Criando network 'web'..."
    docker network create web
fi

# Escolher o que fazer
echo ""
echo "Opções de deploy:"
echo "1) 🤖 Apenas aplicação Assistente"
echo "2) 🏗️ Apenas infraestrutura base"  
echo "3) 🌟 Deploy completo (base + aplicação)"
echo ""

choice=${1:-}
if [ -z "$choice" ]; then
    read -p "Escolha [1-3]: " choice
fi

case $choice in
    1|app|aplicacao)
        log "🤖 Deploy da aplicação..."
        cd ../apps/assistente
        docker-compose pull
        docker-compose up -d
        log "✅ Aplicação deployada!"
        ;;
    2|base|infra)
        log "🏗️ Deploy da infraestrutura base..."
        cd ../base
        docker-compose pull
        docker-compose up -d
        log "✅ Base deployada!"
        ;;
    3|all|completo)
        log "🌟 Deploy completo..."
        
        # Base primeiro
        cd ../base
        docker-compose pull
        docker-compose up -d
        log "✅ Base iniciada"
        
        # Aguardar Traefik
        sleep 10
        
        # Aplicação
        cd ../apps/assistente
        docker-compose pull
        docker-compose up -d
        log "✅ Aplicação iniciada"
        ;;
    *)
        warn "Opção inválida: $choice"
        exit 1
        ;;
esac

# Status final
sleep 5
log "📊 Status final:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
log "🎉 Deploy concluído!"
echo ""
echo "🌐 URLs de acesso:"
echo "  • API: http://localhost:7000"
echo "  • Flower: http://localhost:5555"
echo "  • Portainer: http://localhost:9000"