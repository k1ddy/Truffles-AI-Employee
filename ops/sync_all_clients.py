#!/usr/bin/env python3
"""
Синхронизация базы знаний для ВСЕХ клиентов.
Запускать вручную или через cron.

Что делает:
1. Загружает список активных клиентов из БД
2. Для каждого клиента: скачивает документы из Google Drive
3. Разбивает на chunks, создаёт embeddings
4. Загружает в Qdrant с metadata.client_slug
"""
import subprocess
import requests
import hashlib
import re
import json
import os
from pathlib import Path

# === КОНФИГ ===
BGE_URL = "http://172.24.0.8:80/embed"
QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_COLLECTION = "truffles_knowledge"
QDRANT_API_KEY = "Iddqd777!"

def get_clients():
    """Получить список активных клиентов из БД"""
    result = subprocess.run([
        'docker', 'exec', 'truffles_postgres_1',
        'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-A', '-c',
        "SELECT name, config->>'folder_id' FROM clients WHERE status = 'active'"
    ], capture_output=True, text=True)
    
    clients = []
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            name, folder_id = line.split('|')
            if folder_id:
                clients.append({'name': name, 'folder_id': folder_id})
    return clients

def get_embedding(text):
    """Получить embedding от BGE-M3"""
    resp = requests.post(BGE_URL, json={"inputs": text}, timeout=30)
    return resp.json()[0]

def upsert_to_qdrant(points):
    """Загрузить points в Qdrant"""
    resp = requests.put(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
        headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
        json={"points": points},
        timeout=60
    )
    return resp.json()

def delete_client_docs(client_slug):
    """Удалить все документы клиента из Qdrant"""
    resp = requests.post(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/delete",
        headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
        json={
            "filter": {
                "must": [
                    {"key": "metadata.client_slug", "match": {"value": client_slug}}
                ]
            }
        },
        timeout=30
    )
    return resp.json()

def split_into_chunks(text, doc_name, doc_id, client_slug):
    """Разбить текст на chunks по заголовкам"""
    chunks = []
    sections = re.split(r'\n(?=##?\s)', text)
    
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 50:
            continue
        
        lines = section.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"Section {i}"
        
        chunks.append({
            "content": section,
            "metadata": {
                "client_slug": client_slug,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "section_title": title,
                "section_index": i
            }
        })
    
    return chunks

def sync_client(client_name, docs_dir):
    """Синхронизировать документы одного клиента"""
    print(f"\n=== {client_name} ===")
    
    if not os.path.exists(docs_dir):
        print(f"  Папка не найдена: {docs_dir}")
        return 0
    
    # Собираем все .md файлы
    files = [f for f in os.listdir(docs_dir) if f.endswith('.md')]
    if not files:
        print(f"  Нет .md файлов")
        return 0
    
    print(f"  Найдено файлов: {len(files)}")
    
    # Удаляем старые документы клиента
    print(f"  Удаляю старые документы...")
    delete_client_docs(client_name)
    
    # Обрабатываем каждый файл
    all_points = []
    point_id = hash(client_name) % 100000000  # Уникальный начальный ID для клиента
    
    for filename in files:
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        chunks = split_into_chunks(content, filename, doc_id, client_name)
        print(f"  {filename}: {len(chunks)} chunks")
        
        for chunk in chunks:
            vector = get_embedding(chunk["content"])
            all_points.append({
                "id": point_id,
                "vector": vector,
                "payload": chunk
            })
            point_id += 1
    
    if all_points:
        print(f"  Загружаю {len(all_points)} chunks в Qdrant...")
        result = upsert_to_qdrant(all_points)
        if result.get("status") == "ok":
            print(f"  ✅ Успешно!")
        else:
            print(f"  ❌ Ошибка: {result}")
    
    return len(all_points)

def main():
    print("=== Синхронизация базы знаний ===\n")
    
    # Получаем клиентов
    clients = get_clients()
    print(f"Активных клиентов: {len(clients)}")
    
    # Папки с документами (локальные копии)
    # В реальности нужно скачивать из Google Drive
    demo_salon_docs = Path("/home/zhan/truffles/knowledge/demo_salon")
    if not demo_salon_docs.exists():
        demo_salon_docs = Path("/home/zhan/truffles/ops/demo_salon_docs")

    docs_dirs = {
        'truffles': '/home/zhan/truffles/knowledge',  # или где лежат файлы
        'demo_salon': str(demo_salon_docs),
    }
    
    total_chunks = 0
    for client in clients:
        name = client['name']
        docs_dir = docs_dirs.get(name)
        if docs_dir:
            total_chunks += sync_client(name, docs_dir)
        else:
            print(f"\n⚠️  {name}: папка с документами не настроена")
    
    print(f"\n=== Итого: {total_chunks} chunks ===")

if __name__ == "__main__":
    main()
