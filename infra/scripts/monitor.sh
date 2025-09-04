#!/bin/bash
# Script para monitorar status dos serviços
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo "🔍 Monitor da Infraestrutura Assistente"
echo "======================================"

# Função para verificar saúde de um serviço
check_health() {
    local container=$1
    local url=$2
    local name=$3
    
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        if [ ! -z "$url" ]; then
            if curl -s -f "$url" >/dev/null 2>&1; then
                echo -e "✅ ${GREEN}$name${NC} - Rodando e responsivo"
            else
                echo -e "⚠️  ${YELLOW}$name${NC} - Rodando mas sem resposta HTTP"
            fi
        else
            echo -e "✅ ${GREEN}$name${NC} - Rodando"
        fi
    else
        echo -e "❌ ${RED}$name${NC} - Parado"
    fi
}

# Status dos containers
echo ""
echo "📊 Status dos Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(assistente|traefik|portainer|mailserver)" || echo "Nenhum container encontrado"

echo ""
echo "🏥 Saúde dos Serviços:"

# Verificar cada serviço
check_health "traefik" "http://localhost:8080/ping" "Traefik"
check_health "portainer" "http://localhost:9000" "Portainer"
check_health "assistente_postgres" "" "PostgreSQL"
check_health "assistente_redis" "" "Redis"
check_health "assistente_api" "http://localhost:7000/" "API Assistente"
check_health "assistente_worker" "" "Celery Worker"
check_health "assistente_beat" "" "Celery Beat"
check_health "assistente_flower" "http://localhost:5555/" "Flower"
check_health "mailserver" "" "Servidor Email"
check_health "roundcube" "" "Roundcube Webmail"

echo ""
echo "💾 Uso de Recursos:"

# CPU e Memória dos containers
echo "Container               CPU %    MEM Usage"
echo "----------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(assistente|traefik|portainer|mailserver)" || echo "Dados não disponíveis"

echo ""
echo "📦 Volumes:"
docker volume ls | grep -E "(assistente|traefik|portainer|mailserver)" || echo "Nenhum volume encontrado"

echo ""
echo "🌐 Networks:"
docker network ls | grep -E "(assistente|web|email)" || echo "Nenhuma network encontrada"

echo ""
echo "🔗 URLs de Acesso:"
echo "  • API Principal: http://localhost:7000"
echo "  • Flower (Celery): http://localhost:5555"
echo "  • Portainer: http://localhost:9000"
echo "  • Traefik Dashboard: http://localhost:8080"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"

echo ""
echo "⏱️ Última atualização: $(date '+%Y-%m-%d %H:%M:%S')"