#!/bin/bash

HEALTH_URL="http://localhost:8000/health"
TELEGRAM_BOT="REDACTED_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT="1969855532"
ALERT_FILE="/tmp/truffles_alert_sent"

response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 $HEALTH_URL 2>/dev/null)

if [ "$response" != "200" ]; then
    if [ ! -f $ALERT_FILE ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT" \
            -d "text=🔴 ALERT: truffles-api DOWN! HTTP $response" > /dev/null
        touch $ALERT_FILE
        echo "$(date): ALERT sent - HTTP $response"
    fi
else
    if [ -f $ALERT_FILE ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT" \
            -d "text=✅ RECOVERED: truffles-api is UP" > /dev/null
        rm -f $ALERT_FILE
        echo "$(date): RECOVERED"
    fi
fi
