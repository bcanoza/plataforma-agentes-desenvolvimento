#!/bin/bash
# Script para visualizar logs dos serviços
set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo "📋 Script de Logs - Infraestrutura Assistente"
    echo ""
    echo "Uso: $0 [serviço] [opções]"
    echo ""
    echo "Serviços disponíveis:"
    echo "  api      - API Principal"
    echo "  worker   - Celery Worker"  
    echo "  beat     - Celery Beat"
    echo "  flower   - Flower Monitor"
    echo "  postgres - PostgreSQL"
    echo "  redis    - Redis"
    echo "  traefik  - Traefik Proxy"
    echo "  email    - Servidor Email"
    echo "  all      - Todos os serviços"
    echo ""
    echo "Opções:"
    echo "  -f       - Seguir logs (tail -f)"
    echo "  -n NUM   - Mostrar últimas NUM linhas"
    echo "  --help   - Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0 api -f              # Seguir logs da API"
    echo "  $0 worker -n 100       # Últimas 100 linhas do worker"
    echo "  $0 all                 # Logs de todos os serviços"
}

# Verificar argumentos
if [ $# -eq 0 ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

SERVICE=$1
FOLLOW=""
LINES="50"

# Processar opções
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        -f)
            FOLLOW="-f"
            shift
            ;;
        -n)
            LINES="$2"
            shift 2
            ;;
        *)
            echo "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Mapear serviços para containers
declare -A CONTAINERS=(
    ["api"]="assistente_api"
    ["worker"]="assistente_worker"
    ["beat"]="assistente_beat"
    ["flower"]="assistente_flower"
    ["postgres"]="assistente_postgres"
    ["redis"]="assistente_redis"
    ["traefik"]="traefik"
    ["portainer"]="portainer"
    ["email"]="mailserver"
    ["roundcube"]="roundcube"
)

show_logs() {
    local container=$1
    local service_name=$2
    
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${BLUE}📋 Logs do $service_name (${container}):${NC}"
        echo "----------------------------------------"
        docker logs $FOLLOW --tail="$LINES" "$container"
        echo ""
    else
        echo -e "${YELLOW}⚠️ Container $container não está rodando${NC}"
    fi
}

if [ "$SERVICE" == "all" ]; then
    echo -e "${GREEN}📊 Logs de Todos os Serviços${NC}"
    echo "========================================="
    
    for service in api worker beat flower postgres redis traefik; do
        container=${CONTAINERS[$service]}
        if [ ! -z "$container" ]; then
            show_logs "$container" "$service"
        fi
    done
else
    # Verificar se serviço existe
    if [ -z "${CONTAINERS[$SERVICE]}" ]; then
        echo "❌ Serviço '$SERVICE' não encontrado"
        show_help
        exit 1
    fi
    
    container=${CONTAINERS[$SERVICE]}
    show_logs "$container" "$SERVICE"
fi

echo -e "${GREEN}✅ Visualização de logs concluída${NC}"