#!/bin/bash
docker exec client_zero_postgres_1 psql -U n8n -d truffles-chat-bot -c "SELECT name, text, active FROM prompts WHERE name = 'intent_classifier';"
