#!/bin/bash
# Script de monitoramento da infraestrutura

clear
echo "📊 Monitor da Infraestrutura Assistente"
echo "======================================="
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verificar saúde de um container
check_container() {
    local name=$1
    local url=$2
    
    if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        if [ ! -z "$url" ]; then
            if curl -s -f "$url" >/dev/null 2>&1; then
                echo -e "✅ ${GREEN}$name${NC} - Rodando e responsivo"
            else
                echo -e "⚠️ ${YELLOW}$name${NC} - Rodando mas sem resposta"
            fi
        else
            echo -e "✅ ${GREEN}$name${NC} - Rodando"
        fi
    else
        echo -e "❌ ${RED}$name${NC} - Parado"
    fi
}

# Status dos containers
echo "🐳 Status dos Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(assistente|traefik|portainer)" || echo "Nenhum container encontrado"

echo ""
echo "🏥 Saúde dos Serviços:"
check_container "traefik" "http://localhost:8080/ping"
check_container "portainer" "http://localhost:9000"
check_container "assistente_postgres" ""
check_container "assistente_redis" ""
check_container "assistente_api" "http://localhost:7000/"
check_container "assistente_worker" ""
check_container "assistente_beat" ""
check_container "assistente_flower" "http://localhost:5555/"

echo ""
echo "💾 Uso de Recursos:"
echo "Container           CPU %    Mem Usage"
echo "------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(assistente|traefik|portainer)" 2>/dev/null || echo "Dados não disponíveis"

echo ""
echo "📦 Volumes:"
docker volume ls | grep assistente || echo "Nenhum volume encontrado"

echo ""
echo "🌐 Networks:"
docker network ls | grep -E "(assistente|web)" || echo "Networks não encontradas"

echo ""
echo "🔗 URLs de Acesso:"
echo "  • API Principal: http://localhost:7000"
echo "  • API Docs: http://localhost:7000/docs"
echo "  • Flower (Celery): http://localhost:5555"
echo "  • Portainer: http://localhost:9000"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"

echo ""
echo "⏱️ Última atualização: $(date)"