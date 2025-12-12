#!/bin/bash
# Qdrant backup script
# Runs weekly via cron, keeps 4 weeks

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/home/zhan/backups/qdrant
LOG=/home/zhan/logs/backup.log

echo "[$DATE] Starting Qdrant backup..." >> $LOG

# Create snapshot via API
RESULT=$(curl -s -X POST "http://localhost:6333/collections/truffles_knowledge/snapshots")

if echo "$RESULT" | grep -q '"status":"ok"'; then
    SNAPSHOT=$(echo "$RESULT" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    echo "[$DATE] Qdrant snapshot created: $SNAPSHOT" >> $LOG
    
    # Copy snapshot to backup dir
    mkdir -p $BACKUP_DIR
    cp /var/lib/docker/volumes/qdrant_storage/_data/snapshots/truffles_knowledge/$SNAPSHOT "$BACKUP_DIR/" 2>/dev/null || \
    docker cp qdrant:/qdrant/storage/snapshots/truffles_knowledge/$SNAPSHOT "$BACKUP_DIR/"
    
    echo "[$DATE] Qdrant backup done." >> $LOG
else
    echo "[$DATE] ERROR: Qdrant backup failed! $RESULT" >> $LOG
    exit 1
fi

# Delete backups older than 28 days
find $BACKUP_DIR -name "*.snapshot" -mtime +28 -delete
