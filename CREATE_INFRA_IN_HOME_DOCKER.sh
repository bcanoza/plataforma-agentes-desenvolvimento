#!/bin/bash
# Execute este script em /home/docker para criar a infraestrutura

echo "🏗️ Criando Infraestrutura Docker em /home/docker"
echo "================================================="

# Verificar se estamos no local correto
if [ "$(pwd)" != "/home/docker" ]; then
    echo "❌ Este script deve ser executado de /home/docker"
    echo "Execute: cd /home/docker && bash CREATE_INFRA_IN_HOME_DOCKER.sh"
    exit 1
fi

echo "📁 Criando estrutura de diretórios..."
mkdir -p infra/{base,email,apps/assistente,scripts}
mkdir -p infra/{base,email,apps/assistente}/config

echo "✅ Estrutura criada!"
echo ""
echo "🐳 Agora execute os próximos scripts para criar os arquivos..."
echo ""
echo "Próximo passo:"
echo "  bash CREATE_DOCKER_COMPOSE_FILES.sh"