#!/bin/bash
# Gerenciador Principal da Infraestrutura Assistente

clear
echo "🤖 Gerenciador da Aplicação Assistente"
echo "======================================"
echo ""
echo "📍 Localização: $(pwd)"
echo ""

# Verificar se estamos no lugar certo
if [ ! -f "../apps/assistente/docker-compose.yml" ]; then
    echo "❌ Execute este script de: infra/scripts/"
    exit 1
fi

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }

echo "📋 OPERAÇÕES DISPONÍVEIS:"
echo ""
echo "  🚀 APLICAÇÃO"
echo "    1) start-app      - Iniciar aplicação Assistente"
echo "    2) stop-app       - Parar aplicação"
echo "    3) restart-app    - Reiniciar aplicação"
echo "    4) rebuild-app    - Rebuild completo"
echo ""
echo "  🏗️ INFRAESTRUTURA"  
echo "    5) start-base     - Iniciar base (Traefik + Portainer)"
echo "    6) start-all      - Iniciar tudo (base + aplicação)"
echo "    7) stop-all       - Parar tudo"
echo ""
echo "  📊 MONITORAMENTO"
echo "    8) status         - Status geral"
echo "    9) logs-api       - Logs da API"
echo "   10) logs-worker    - Logs do Worker"
echo "   11) logs-all       - Logs de todos"
echo ""
echo "  🔧 MANUTENÇÃO"
echo "   12) scale-workers  - Escalar Workers"
echo "   13) backup-db      - Backup PostgreSQL"
echo "   14) connect-db     - Conectar PostgreSQL"
echo ""
echo "    0) Sair"
echo ""

read -p "Escolha uma opção [0-14]: " choice

case $choice in
    1)
        log "🚀 Iniciando aplicação..."
        cd ../apps/assistente
        docker-compose up -d
        log "✅ Aplicação iniciada!"
        echo "🌐 API: http://localhost:7000"
        echo "🌺 Flower: http://localhost:5555"
        ;;
    2)
        log "🛑 Parando aplicação..."
        cd ../apps/assistente
        docker-compose down
        log "✅ Aplicação parada!"
        ;;
    3)
        log "🔄 Reiniciando aplicação..."
        cd ../apps/assistente
        docker-compose restart
        log "✅ Aplicação reiniciada!"
        ;;
    4)
        log "🔨 Rebuild completo..."
        cd ../apps/assistente
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        log "✅ Rebuild concluído!"
        ;;
    5)
        log "🏗️ Iniciando infraestrutura base..."
        cd ../base
        docker-compose up -d
        log "✅ Base iniciada (Traefik + Portainer)!"
        ;;
    6)
        log "🌟 Iniciando infraestrutura completa..."
        cd ../base && docker-compose up -d
        sleep 5
        cd ../apps/assistente && docker-compose up -d
        log "✅ Tudo iniciado!"
        ;;
    7)
        log "🛑 Parando toda infraestrutura..."
        cd ../apps/assistente && docker-compose down
        cd ../base && docker-compose down  
        log "✅ Tudo parado!"
        ;;
    8)
        log "📊 Status geral:"
        echo ""
        echo "🏗️ INFRAESTRUTURA BASE:"
        cd ../base && docker-compose ps
        echo ""
        echo "🤖 APLICAÇÃO ASSISTENTE:"
        cd ../apps/assistente && docker-compose ps
        ;;
    9)
        log "📋 Logs da API (tempo real):"
        docker logs -f assistente_api
        ;;
    10)
        log "📋 Logs do Worker (tempo real):"
        docker logs -f assistente_worker
        ;;
    11)
        log "📋 Logs de todos os serviços:"
        cd ../apps/assistente
        docker-compose logs --tail=50
        ;;
    12)
        echo -n "Quantos workers? [1-8]: "
        read workers
        log "⚙️ Escalando para $workers workers..."
        cd ../apps/assistente
        docker-compose up -d --scale worker=$workers
        log "✅ Workers escalados!"
        ;;
    13)
        log "💾 Backup do PostgreSQL..."
        timestamp=$(date +%Y%m%d_%H%M%S)
        docker exec assistente_postgres pg_dump -U app_writer -d assistente > "../../backup_$timestamp.sql"
        log "✅ Backup salvo: backup_$timestamp.sql"
        ;;
    14)
        log "🐘 Conectando no PostgreSQL..."
        docker exec -it assistente_postgres psql -U app_writer -d assistente
        ;;
    0)
        log "👋 Até logo!"
        exit 0
        ;;
    *)
        error "Opção inválida!"
        ;;
esac