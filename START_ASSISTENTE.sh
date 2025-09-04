#!/bin/bash
# Script de início rápido para a aplicação Assistente

echo "🚀 Iniciando Aplicação Assistente"
echo "=================================="
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado! Instale o Docker primeiro."
    exit 1
fi

# Criar network se não existir
if ! docker network ls | grep -q "web"; then
    echo "🌐 Criando network 'web'..."
    docker network create web
fi

echo "📍 Localização: $(pwd)"
echo ""
echo "Escolha como iniciar:"
echo ""
echo "1) 🎮 Gerenciador Interativo (RECOMENDADO)"
echo "2) ⚡ Início Rápido (docker-compose simples)"
echo "3) 🏗️ Deploy Modular Completo"
echo "4) 📊 Apenas Ver Status"
echo ""
read -p "Escolha [1-4]: " choice

case $choice in
    1)
        echo "🎮 Abrindo gerenciador interativo..."
        cd infra/scripts
        ./manage.sh
        ;;
    2)
        echo "⚡ Início rápido..."
        docker-compose up -d
        echo ""
        echo "✅ Aplicação iniciada!"
        echo "🌐 API: http://localhost:7000"
        echo "🌺 Flower: http://localhost:5555"
        ;;
    3)
        echo "🏗️ Deploy modular..."
        cd infra/scripts
        ./deploy.sh all
        ;;
    4)
        echo "📊 Status atual:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "🎉 Operação concluída!"
echo ""
echo "Para monitorar: cd infra/scripts && ./monitor.sh"
echo "Para logs: cd infra/scripts && ./logs.sh api -f"