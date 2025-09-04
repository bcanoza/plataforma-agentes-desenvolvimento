#!/bin/bash
# Script para copiar a infraestrutura para seu diretório de trabalho

echo "🏗️ Script de Cópia da Infraestrutura Docker"
echo "============================================="
echo ""

# Verificar onde estamos
echo "📍 Localização atual: $(pwd)"
echo "📁 Conteúdo disponível:"
ls -la infra/ 2>/dev/null || echo "❌ Pasta infra não encontrada aqui"

echo ""
echo "🎯 Onde você quer copiar a infraestrutura?"
echo ""
echo "Opções comuns:"
echo "  1) /home/docker"
echo "  2) /home/docker/assistente" 
echo "  3) /opt/assistente"
echo "  4) Digitar caminho personalizado"
echo ""

read -p "Escolha uma opção [1-4]: " choice

case $choice in
    1) 
        TARGET_DIR="/home/docker"
        ;;
    2)
        TARGET_DIR="/home/docker/assistente" 
        ;;
    3)
        TARGET_DIR="/opt/assistente"
        ;;
    4)
        read -p "Digite o caminho completo: " TARGET_DIR
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

echo ""
echo "🎯 Diretório de destino: $TARGET_DIR"

# Verificar se diretório existe
if [ ! -d "$TARGET_DIR" ]; then
    echo "📁 Diretório não existe. Criando..."
    sudo mkdir -p "$TARGET_DIR"
fi

# Verificar permissões
if [ ! -w "$TARGET_DIR" ]; then
    echo "🔐 Sem permissão de escrita. Usando sudo..."
    SUDO_NEEDED="sudo"
else
    SUDO_NEEDED=""
fi

echo ""
echo "📦 Copiando estrutura..."

# Copiar tudo
$SUDO_NEEDED cp -r infra/ "$TARGET_DIR/"
$SUDO_NEEDED cp -r app/ "$TARGET_DIR/"
$SUDO_NEEDED cp .env.example "$TARGET_DIR/"
$SUDO_NEEDED cp MIGRATION_GUIDE.md "$TARGET_DIR/"
$SUDO_NEEDED cp DOCKER_INFRASTRUCTURE_SUMMARY.md "$TARGET_DIR/"
$SUDO_NEEDED cp docker-compose.yml "$TARGET_DIR/"

# Ajustar permissões
if [ ! -z "$SUDO_NEEDED" ]; then
    $SUDO_NEEDED chown -R $USER:$USER "$TARGET_DIR/"
fi

# Tornar scripts executáveis
chmod +x "$TARGET_DIR/infra/scripts/"*.sh

echo "✅ Infraestrutura copiada com sucesso!"
echo ""
echo "🚀 Próximos passos:"
echo ""
echo "1. Navegar para o diretório:"
echo "   cd $TARGET_DIR"
echo ""
echo "2. Configurar ambiente:"
echo "   cd infra/apps/assistente"
echo "   cp .env.example .env"
echo "   nano .env  # Editar configurações"
echo ""
echo "3. Iniciar infraestrutura:"
echo "   cd ../../scripts"
echo "   ./manage.sh"
echo ""
echo "OU usar deploy direto:"
echo "   ./deploy.sh all"
echo ""
echo "📊 Monitorar status:"
echo "   ./monitor.sh"
echo ""
echo "📋 Ver logs:"
echo "   ./logs.sh api -f"
echo ""
echo "🎉 Sua infraestrutura Docker está pronta!"
echo ""
echo "📍 Localização final: $TARGET_DIR/infra/"