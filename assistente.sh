#!/bin/bash
# Script principal para gerenciar a aplicação Assistente
# ✅ Preserva docker-compose.yml original (Traefik + Portainer)
# 🤖 Gerencia docker-compose.assistente.yml (aplicação)

clear
echo "🤖 Gerenciador da Aplicação Assistente"
echo "======================================"
echo ""
echo "📍 Localização: $(pwd)"

# Verificar arquivos necessários
if [ ! -f "docker-compose.assistente.yml" ]; then
    echo "❌ docker-compose.assistente.yml não encontrado!"
    echo "Certifique-se de estar na raiz do projeto."
    exit 1
fi

if [ ! -f "app/Dockerfile" ]; then
    echo "⚠️ app/Dockerfile não encontrado. Será necessário criá-lo."
fi

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

# Menu
echo "📋 OPERAÇÕES DISPONÍVEIS:"
echo ""
echo "  🚀 CONTROLE DA APLICAÇÃO"
echo "    1) start          - Iniciar aplicação Assistente"
echo "    2) stop           - Parar aplicação Assistente"  
echo "    3) restart        - Reiniciar aplicação"
echo "    4) rebuild        - Rebuild e restart"
echo ""
echo "  📊 MONITORAMENTO"
echo "    5) status         - Ver status dos serviços"
echo "    6) logs           - Logs da aplicação"
echo "    7) logs-api       - Logs apenas da API"
echo "    8) logs-worker    - Logs apenas do Worker"
echo ""
echo "  🔧 MANUTENÇÃO"
echo "    9) scale-worker   - Escalar Workers"
echo "   10) backup         - Backup do banco"
echo "   11) psql           - Conectar no PostgreSQL"
echo ""
echo "  🏗️ INFRAESTRUTURA COMPLETA"
echo "   12) infra-start    - Iniciar infraestrutura completa (Traefik + Assistente)"
echo "   13) infra-stop     - Parar toda infraestrutura"
echo "   14) infra-status   - Status de toda infraestrutura"
echo ""
echo "    0) Sair"
echo ""

read -p "Escolha uma opção [0-14]: " choice

case $choice in
    1)
        log "🚀 Iniciando aplicação Assistente..."
        docker-compose -f docker-compose.assistente.yml up -d
        log "✅ Aplicação iniciada!"
        echo ""
        echo "🌐 Acessos:"
        echo "  • API: http://localhost:7000"
        echo "  • Flower: http://localhost:5555"
        ;;
    2)
        log "🛑 Parando aplicação Assistente..."
        docker-compose -f docker-compose.assistente.yml down
        log "✅ Aplicação parada!"
        ;;
    3)
        log "🔄 Reiniciando aplicação..."
        docker-compose -f docker-compose.assistente.yml restart
        log "✅ Aplicação reiniciada!"
        ;;
    4)
        log "🔨 Rebuild e restart..."
        docker-compose -f docker-compose.assistente.yml down
        docker-compose -f docker-compose.assistente.yml build --no-cache
        docker-compose -f docker-compose.assistente.yml up -d
        log "✅ Rebuild concluído!"
        ;;
    5)
        log "📊 Status da aplicação:"
        docker-compose -f docker-compose.assistente.yml ps
        ;;
    6)
        log "📋 Logs da aplicação (últimas 50 linhas):"
        docker-compose -f docker-compose.assistente.yml logs --tail=50
        ;;
    7)
        log "📋 Logs da API (tempo real):"
        docker logs -f assistente_api
        ;;
    8)
        log "📋 Logs do Worker (tempo real):"
        docker logs -f assistente_worker
        ;;
    9)
        echo -n "Quantos workers? [1-8]: "
        read workers
        log "⚙️ Escalando para $workers workers..."
        docker-compose -f docker-compose.assistente.yml up -d --scale worker=$workers
        log "✅ Workers escalados para $workers!"
        ;;
    10)
        log "💾 Fazendo backup do PostgreSQL..."
        timestamp=$(date +%Y%m%d_%H%M%S)
        docker exec assistente_postgres pg_dump -U app_writer -d assistente > "backup_assistente_$timestamp.sql"
        log "✅ Backup salvo: backup_assistente_$timestamp.sql"
        ;;
    11)
        log "🐘 Conectando no PostgreSQL..."
        docker exec -it assistente_postgres psql -U app_writer -d assistente
        ;;
    12)
        log "🏗️ Iniciando infraestrutura completa..."
        docker-compose up -d  # Traefik + Portainer
        sleep 5
        docker-compose -f docker-compose.assistente.yml up -d  # Aplicação
        log "✅ Infraestrutura completa iniciada!"
        echo ""
        echo "🌐 Acessos:"
        echo "  • API: http://localhost:7000"
        echo "  • Flower: http://localhost:5555" 
        echo "  • Portainer: http://localhost:9000"
        ;;
    13)
        log "🛑 Parando toda infraestrutura..."
        docker-compose -f docker-compose.assistente.yml down
        docker-compose down
        log "✅ Toda infraestrutura parada!"
        ;;
    14)
        log "📊 Status de toda infraestrutura:"
        echo ""
        echo "🏗️ INFRAESTRUTURA BASE:"
        docker-compose ps
        echo ""
        echo "🤖 APLICAÇÃO ASSISTENTE:"
        docker-compose -f docker-compose.assistente.yml ps
        echo ""
        echo "📈 RECURSOS:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ;;
    0)
        log "👋 Até logo!"
        exit 0
        ;;
    *)
        error "Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "✅ Operação concluída!"