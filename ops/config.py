# Truffles Ops Config
# IP адреса docker контейнеров (для запуска с хоста, не из контейнера)

QDRANT_HOST = '172.24.0.3'
QDRANT_PORT = 6333
QDRANT_URL = f'http://{QDRANT_HOST}:{QDRANT_PORT}'
QDRANT_API_KEY = 'Iddqd777!'

POSTGRES_HOST = 'localhost'
POSTGRES_PORT = 5432
POSTGRES_DB = 'chatbot'
POSTGRES_USER = 'n8n'
POSTGRES_PASSWORD = 'Iddqd777!'

# Для использования внутри docker network:
# QDRANT_HOST = 'qdrant'
