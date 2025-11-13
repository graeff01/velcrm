#!/bin/bash

# ========================================
# SCRIPT DE BACKUP DO BANCO DE DADOS CRM
# ========================================
# Uso: ./backup_database.sh
# Cron: 0 2 * * * /caminho/para/backup_database.sh

set -e  # Parar em caso de erro

# Configurações
DB_PATH="/home/user/crmwhatsapp/backend/crm_whatsapp.db"
BACKUP_DIR="/home/user/crmwhatsapp/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/crm_backup_$TIMESTAMP.db"
RETENTION_DAYS=30

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🗄️  BACKUP DO BANCO DE DADOS CRM${NC}"
echo -e "${GREEN}========================================${NC}"

# Criar diretório de backup se não existir
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}📁 Criando diretório de backup...${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Verificar se banco existe
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ Erro: Banco de dados não encontrado em $DB_PATH${NC}"
    exit 1
fi

# Fazer backup
echo -e "${YELLOW}💾 Fazendo backup do banco...${NC}"
cp "$DB_PATH" "$BACKUP_FILE"

# Verificar se backup foi criado
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
else
    echo -e "${RED}❌ Erro ao criar backup${NC}"
    exit 1
fi

# Comprimir backup
echo -e "${YELLOW}🗜️  Comprimindo backup...${NC}"
gzip "$BACKUP_FILE"

if [ -f "$BACKUP_FILE.gz" ]; then
    COMPRESSED_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
    echo -e "${GREEN}✅ Backup comprimido: $BACKUP_FILE.gz ($COMPRESSED_SIZE)${NC}"
else
    echo -e "${RED}❌ Erro ao comprimir backup${NC}"
    exit 1
fi

# Limpar backups antigos
echo -e "${YELLOW}🗑️  Removendo backups com mais de $RETENTION_DAYS dias...${NC}"
find "$BACKUP_DIR" -name "crm_backup_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

# Contar backups existentes
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "crm_backup_*.db.gz" -type f | wc -l)
echo -e "${GREEN}📊 Total de backups: $BACKUP_COUNT${NC}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ BACKUP CONCLUÍDO COM SUCESSO!${NC}"
echo -e "${GREEN}========================================${NC}"
