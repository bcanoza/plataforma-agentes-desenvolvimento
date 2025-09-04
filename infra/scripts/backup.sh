#!/bin/bash
# Script para backup dos dados importantes
set -e

echo "💾 Iniciando backup da infraestrutura..."

# Configurações
BACKUP_DIR="./backups/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$BACKUP_DIR"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# 1. Backup do PostgreSQL
log "📊 Fazendo backup do PostgreSQL..."
if docker ps --format '{{.Names}}' | grep -q "assistente_postgres"; then
    docker exec assistente_postgres pg_dump -U app_writer -d assistente > "$BACKUP_DIR/postgres_assistente.sql"
    log "✅ Backup PostgreSQL salvo: $BACKUP_DIR/postgres_assistente.sql"
else
    log "⚠️ PostgreSQL não está rodando, pulando backup"
fi

# 2. Backup do Redis (dados persistentes)
log "🔴 Fazendo backup do Redis..."
if docker ps --format '{{.Names}}' | grep -q "assistente_redis"; then
    docker exec assistente_redis redis-cli BGSAVE
    sleep 2
    docker cp assistente_redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"
    log "✅ Backup Redis salvo: $BACKUP_DIR/redis_dump.rdb"
else
    log "⚠️ Redis não está rodando, pulando backup"
fi

# 3. Backup dos volumes Docker
log "📁 Fazendo backup dos volumes..."
docker run --rm -v assistente_postgres_data:/backup-source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_volume.tar.gz -C /backup-source .
docker run --rm -v assistente_redis_data:/backup-source -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/redis_volume.tar.gz -C /backup-source .

# 4. Backup das configurações
log "⚙️ Fazendo backup das configurações..."
cp -r ../base/config "$BACKUP_DIR/base_config" 2>/dev/null || true
cp -r ../email/config "$BACKUP_DIR/email_config" 2>/dev/null || true
cp -r ../apps/assistente/config "$BACKUP_DIR/app_config" 2>/dev/null || true

# 5. Backup dos docker-compose files
log "🐳 Fazendo backup dos docker-compose..."
cp ../base/docker-compose.yml "$BACKUP_DIR/docker-compose-base.yml"
cp ../email/docker-compose.yml "$BACKUP_DIR/docker-compose-email.yml"
cp ../apps/assistente/docker-compose.yml "$BACKUP_DIR/docker-compose-assistente.yml"

# 6. Criar script de restore
cat > "$BACKUP_DIR/restore.sh" << 'EOF'
#!/bin/bash
# Script de restore automático
echo "🔄 Restaurando backup..."

# Parar serviços
cd ../scripts
./stop.sh

# Restaurar volumes
echo "📁 Restaurando volumes..."
docker volume create assistente_postgres_data
docker volume create assistente_redis_data

docker run --rm -v "$(pwd)":/backup -v assistente_postgres_data:/restore-target alpine tar xzf /backup/postgres_volume.tar.gz -C /restore-target
docker run --rm -v "$(pwd)":/backup -v assistente_redis_data:/restore-target alpine tar xzf /backup/redis_volume.tar.gz -C /restore-target

# Restaurar configurações
cp -r base_config ../base/config 2>/dev/null || true
cp -r email_config ../email/config 2>/dev/null || true
cp -r app_config ../apps/assistente/config 2>/dev/null || true

# Restaurar docker-compose files
cp docker-compose-base.yml ../base/docker-compose.yml
cp docker-compose-email.yml ../email/docker-compose.yml
cp docker-compose-assistente.yml ../apps/assistente/docker-compose.yml

echo "✅ Restore concluído! Execute './deploy.sh all' para reiniciar"
EOF

chmod +x "$BACKUP_DIR/restore.sh"

# Criar arquivo de informações do backup
cat > "$BACKUP_DIR/backup_info.txt" << EOF
Backup da Infraestrutura Assistente
===================================

Data/Hora: $(date)
Versão Docker: $(docker --version)
Versão Compose: $(docker-compose --version)

Containers incluídos:
$(docker ps --format "{{.Names}} - {{.Status}}" | grep -E "(assistente|traefik|portainer|mailserver)")

Volumes incluídos:
- assistente_postgres_data
- assistente_redis_data

Arquivos incluídos:
- Configurações de todos os serviços
- Docker-compose files
- Script de restore automático

Para restaurar:
1. cd para este diretório
2. ./restore.sh
3. cd ../scripts && ./deploy.sh all
EOF

# Comprimir backup
log "🗜️ Comprimindo backup..."
cd backups
tar czf "$(basename $BACKUP_DIR).tar.gz" "$(basename $BACKUP_DIR)"
cd ..

log "🎉 Backup concluído!"
echo ""
echo "📊 Resumo do Backup:"
echo "  • Diretório: $BACKUP_DIR"
echo "  • Arquivo: backups/$(basename $BACKUP_DIR).tar.gz"
echo "  • Tamanho: $(du -h $BACKUP_DIR | cut -f1)"
echo ""
echo "Para restaurar: cd $BACKUP_DIR && ./restore.sh"