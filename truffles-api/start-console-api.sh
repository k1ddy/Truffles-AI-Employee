#!/bin/bash
# Console API startup script
cd /home/zhan/truffles-main/truffles-api
set -a
source .env
set +a
exec /home/zhan/truffles-main/truffles-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
