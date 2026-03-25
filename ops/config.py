# Truffles Ops Config
# IP адреса docker контейнеров (для запуска с хоста, не из контейнера)
import os

QDRANT_HOST = '172.24.0.3'
QDRANT_PORT = 6333
QDRANT_URL = f'http://{QDRANT_HOST}:{QDRANT_PORT}'
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY') or os.environ.get('DB_PASSWORD') or ''

POSTGRES_HOST = 'localhost'
POSTGRES_PORT = 5432
POSTGRES_DB = 'chatbot'
POSTGRES_USER = os.environ.get('DB_USER', 'postgres')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DB_PASSWORD') or ''

# Для использования внутри docker network:
# QDRANT_HOST = 'qdrant'
