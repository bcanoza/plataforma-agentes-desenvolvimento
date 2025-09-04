#!/bin/bash
# Comandos rápidos para aplicação Assistente

case "$1" in
    "start")
        echo "🚀 Iniciando aplicação..."
        cd ../apps/assistente
        docker-compose up -d
        echo "✅ Aplicação iniciada!"
        echo "🌐 API: http://localhost:7000"
        echo "🌺 Flower: http://localhost:5555"
        ;;
    "stop")
        echo "🛑 Parando aplicação..."
        cd ../apps/assistente
        docker-compose down
        echo "✅ Aplicação parada!"
        ;;
    "restart")
        echo "🔄 Reiniciando..."
        cd ../apps/assistente
        docker-compose restart
        echo "✅ Reiniciado!"
        ;;
    "status")
        echo "📊 Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep assistente
        ;;
    "logs")
        echo "📋 Logs (últimas 50 linhas):"
        cd ../apps/assistente
        docker-compose logs --tail=50
        ;;
    "api")
        echo "📋 Logs da API (tempo real):"
        docker logs -f assistente_api
        ;;
    "worker")
        echo "📋 Logs do Worker (tempo real):"
        docker logs -f assistente_worker
        ;;
    "full-start")
        echo "🌟 Iniciando infraestrutura completa..."
        cd ../base && docker-compose up -d
        sleep 5
        cd ../apps/assistente && docker-compose up -d
        echo "✅ Tudo iniciado!"
        ;;
    "full-stop")
        echo "🛑 Parando tudo..."
        cd ../apps/assistente && docker-compose down
        cd ../base && docker-compose down
        echo "✅ Tudo parado!"
        ;;
    *)
        echo "⚡ Comandos Rápidos - Assistente"
        echo "==============================="
        echo ""
        echo "Uso: $0 [comando]"
        echo ""
        echo "Comandos da aplicação:"
        echo "  start         - Iniciar aplicação"
        echo "  stop          - Parar aplicação"
        echo "  restart       - Reiniciar" 
        echo "  status        - Ver status"
        echo "  logs          - Ver logs"
        echo "  api           - Logs API (tempo real)"
        echo "  worker        - Logs Worker (tempo real)"
        echo ""
        echo "Comandos da infraestrutura:"
        echo "  full-start    - Iniciar tudo (base + app)"
        echo "  full-stop     - Parar tudo"
        echo ""
        echo "Exemplos:"
        echo "  $0 start"
        echo "  $0 status"
        echo "  $0 api"
        echo ""
        echo "Menu completo: ./manage.sh"
        ;;
esac