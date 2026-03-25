#!/bin/bash
# PostgreSQL backup script
# Runs daily via cron, keeps 7 days

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/home/zhan/backups/postgres
CONTAINER=truffles_postgres_1
LOG=/home/zhan/logs/backup.log
DB_USER="${DB_USER:-postgres}"

echo "[$DATE] Starting backup..." >> $LOG

docker exec $CONTAINER pg_dump -U "$DB_USER" chatbot | gzip > "$BACKUP_DIR/chatbot_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    SIZE=$(ls -lh "$BACKUP_DIR/chatbot_$DATE.sql.gz" | awk '{print $5}')
    echo "[$DATE] Backup created: chatbot_$DATE.sql.gz ($SIZE)" >> $LOG
else
    echo "[$DATE] ERROR: Backup failed!" >> $LOG
    exit 1
fi

find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
echo "[$DATE] Cleanup done." >> $LOG
