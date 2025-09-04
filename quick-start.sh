#!/bin/bash
# Comandos rápidos para a aplicação Assistente
# Mantém infraestrutura base (Traefik + Portainer) separada

echo "⚡ Assistente - Comandos Rápidos"
echo "==============================="

case "$1" in
    "start")
        echo "🚀 Iniciando aplicação Assistente..."
        docker-compose -f docker-compose.assistente.yml up -d
        echo "✅ Pronto!"
        echo "🌐 API: http://localhost:7000"
        echo "🌺 Flower: http://localhost:5555"
        ;;
    "stop")
        echo "🛑 Parando aplicação Assistente..."
        docker-compose -f docker-compose.assistente.yml down
        echo "✅ Parado!"
        ;;
    "status")
        echo "📊 Status:"
        docker-compose -f docker-compose.assistente.yml ps
        ;;
    "logs")
        echo "📋 Logs (últimas 50 linhas):"
        docker-compose -f docker-compose.assistente.yml logs --tail=50
        ;;
    "restart")
        echo "🔄 Reiniciando..."
        docker-compose -f docker-compose.assistente.yml restart
        echo "✅ Reiniciado!"
        ;;
    "infra-start")
        echo "🏗️ Iniciando infraestrutura completa..."
        docker-compose up -d
        sleep 3
        docker-compose -f docker-compose.assistente.yml up -d
        echo "✅ Tudo iniciado!"
        ;;
    "infra-stop")
        echo "🛑 Parando tudo..."
        docker-compose -f docker-compose.assistente.yml down
        docker-compose down
        echo "✅ Tudo parado!"
        ;;
    *)
        echo "Uso: $0 [comando]"
        echo ""
        echo "Comandos disponíveis:"
        echo "  start         - Iniciar aplicação Assistente"
        echo "  stop          - Parar aplicação Assistente"  
        echo "  restart       - Reiniciar aplicação"
        echo "  status        - Ver status"
        echo "  logs          - Ver logs"
        echo "  infra-start   - Iniciar infraestrutura completa"
        echo "  infra-stop    - Parar toda infraestrutura"
        echo ""
        echo "Exemplos:"
        echo "  $0 start"
        echo "  $0 status" 
        echo "  $0 logs"
        echo ""
        echo "Para menu interativo: ./assistente.sh"
        ;;
esac