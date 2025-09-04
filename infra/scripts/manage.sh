#!/bin/bash
# Script principal de gerenciamento da infraestrutura
set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Banner
show_banner() {
    clear
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                  🏗️ INFRAESTRUTURA ASSISTENTE 🏗️                  ║"
    echo "║                                                                  ║"
    echo "║            Gerenciador Centralizado Docker Compose              ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Menu principal
show_menu() {
    echo ""
    echo -e "${GREEN}🎮 OPERAÇÕES DISPONÍVEIS:${NC}"
    echo ""
    echo "  📦 DEPLOY"
    echo "    1) deploy-all     - Deploy completo (base + aplicação + email)"
    echo "    2) deploy-base    - Deploy apenas infraestrutura base"
    echo "    3) deploy-app     - Deploy apenas aplicação assistente"
    echo "    4) deploy-email   - Deploy apenas servidor email"
    echo ""
    echo "  🛑 CONTROLE"
    echo "    5) stop-all       - Parar todos os serviços"
    echo "    6) stop-app       - Parar apenas aplicação"
    echo "    7) restart-app    - Reiniciar aplicação"
    echo ""
    echo "  📊 MONITORAMENTO"
    echo "    8) status         - Status geral dos serviços"
    echo "    9) logs           - Visualizar logs (interativo)"
    echo "   10) monitor        - Monitor em tempo real"
    echo ""
    echo "  💾 BACKUP/RESTORE"
    echo "   11) backup         - Backup completo"
    echo "   12) cleanup        - Limpeza de containers/volumes órfãos"
    echo ""
    echo "  🔧 MANUTENÇÃO"
    echo "   13) update         - Atualizar imagens"
    echo "   14) rebuild        - Rebuild completo"
    echo ""
    echo "   0) Sair"
    echo ""
    echo -n -e "${YELLOW}Escolha uma opção [0-14]: ${NC}"
}

# Funções de operação
deploy_all() {
    echo -e "${BLUE}🚀 Deploy Completo${NC}"
    ./deploy.sh all
}

deploy_base() {
    echo -e "${BLUE}🏗️ Deploy Base${NC}"
    cd ../base && docker-compose up -d
    echo -e "${GREEN}✅ Infraestrutura base deployada${NC}"
}

deploy_app() {
    echo -e "${BLUE}📱 Deploy Aplicação${NC}"
    cd ../apps/assistente && docker-compose up -d
    echo -e "${GREEN}✅ Aplicação deployada${NC}"
}

deploy_email() {
    echo -e "${BLUE}📧 Deploy Email${NC}"
    cd ../email && docker-compose up -d
    echo -e "${GREEN}✅ Servidor email deployado${NC}"
}

stop_all() {
    echo -e "${RED}🛑 Parando Todos os Serviços${NC}"
    ./stop.sh
}

stop_app() {
    echo -e "${YELLOW}⏹️ Parando Aplicação${NC}"
    cd ../apps/assistente && docker-compose down
    echo -e "${GREEN}✅ Aplicação parada${NC}"
}

restart_app() {
    echo -e "${BLUE}🔄 Reiniciando Aplicação${NC}"
    cd ../apps/assistente
    docker-compose down
    sleep 3
    docker-compose up -d
    echo -e "${GREEN}✅ Aplicação reiniciada${NC}"
}

show_status() {
    echo -e "${BLUE}📊 Status dos Serviços${NC}"
    ./monitor.sh
}

show_logs() {
    echo -e "${BLUE}📋 Logs - Modo Interativo${NC}"
    echo ""
    echo "Serviços disponíveis:"
    echo "  api worker beat flower postgres redis traefik email all"
    echo ""
    echo -n "Qual serviço? "
    read service
    echo -n "Seguir logs? [y/N] "
    read follow
    
    if [ "$follow" == "y" ] || [ "$follow" == "Y" ]; then
        ./logs.sh "$service" -f
    else
        ./logs.sh "$service"
    fi
}

monitor_realtime() {
    echo -e "${BLUE}📈 Monitor em Tempo Real${NC}"
    watch -n 5 './monitor.sh'
}

run_backup() {
    echo -e "${PURPLE}💾 Iniciando Backup${NC}"
    ./backup.sh
}

cleanup_docker() {
    echo -e "${YELLOW}🧹 Limpeza Docker${NC}"
    echo -n "Remover containers parados? [y/N] "
    read confirm1
    if [ "$confirm1" == "y" ]; then
        docker container prune -f
    fi
    
    echo -n "Remover volumes órfãos? [y/N] "
    read confirm2
    if [ "$confirm2" == "y" ]; then
        docker volume prune -f
    fi
    
    echo -n "Remover images não utilizadas? [y/N] "
    read confirm3
    if [ "$confirm3" == "y" ]; then
        docker image prune -a -f
    fi
    
    echo -e "${GREEN}✅ Limpeza concluída${NC}"
}

update_images() {
    echo -e "${BLUE}🔄 Atualizando Imagens${NC}"
    
    # Atualizar base
    cd ../base && docker-compose pull && docker-compose up -d
    
    # Atualizar email
    cd ../email && docker-compose pull && docker-compose up -d
    
    # Atualizar aplicação
    cd ../apps/assistente && docker-compose pull && docker-compose up -d
    
    echo -e "${GREEN}✅ Imagens atualizadas${NC}"
}

rebuild_all() {
    echo -e "${BLUE}🔨 Rebuild Completo${NC}"
    echo -n "⚠️ Isso irá parar todos os serviços e fazer rebuild. Continuar? [y/N] "
    read confirm
    
    if [ "$confirm" == "y" ]; then
        ./stop.sh
        sleep 5
        
        # Rebuild aplicação (que tem Dockerfile custom)
        cd ../apps/assistente
        docker-compose build --no-cache
        cd ../../scripts
        
        ./deploy.sh all
        echo -e "${GREEN}✅ Rebuild concluído${NC}"
    else
        echo "Operação cancelada"
    fi
}

# Loop principal
while true; do
    show_banner
    show_menu
    read choice
    
    case $choice in
        1) deploy_all ;;
        2) deploy_base ;;
        3) deploy_app ;;
        4) deploy_email ;;
        5) stop_all ;;
        6) stop_app ;;
        7) restart_app ;;
        8) show_status ;;
        9) show_logs ;;
        10) monitor_realtime ;;
        11) run_backup ;;
        12) cleanup_docker ;;
        13) update_images ;;
        14) rebuild_all ;;
        0) 
            echo -e "${GREEN}👋 Até logo!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opção inválida!${NC}"
            sleep 2
            ;;
    esac
    
    echo ""
    echo -n -e "${YELLOW}Pressione Enter para continuar...${NC}"
    read
done