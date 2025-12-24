#!/usr/bin/env python3
"""
Синхронизация базы знаний одного клиента.

Использование:
  python3 sync_client.py <client_slug> [docs_folder]

Примеры:
  python3 sync_client.py demo_salon
  python3 sync_client.py demo_salon /path/to/docs
"""
import subprocess
import requests
import hashlib
import re
import sys
import os

# === КОНФИГ ===
BGE_URL = "http://172.24.0.8:80/embed"
QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_COLLECTION = "truffles_knowledge"
QDRANT_API_KEY = "REDACTED_PASSWORD"

def get_embedding(text):
    """Получить embedding от BGE-M3"""
    resp = requests.post(BGE_URL, json={"inputs": text}, timeout=30)
    return resp.json()[0]

def delete_client_docs(client_slug):
    """Удалить все документы клиента из Qdrant"""
    print(f"Удаляю старые документы {client_slug}...")
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
    result = resp.json()
    if result.get("status") == "ok":
        print("✓ Старые документы удалены")
    return result

def upsert_to_qdrant(points):
    """Загрузить points в Qdrant"""
    resp = requests.put(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
        headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
        json={"points": points},
        timeout=60
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

def sync_folder(client_slug, docs_dir):
    """Синхронизировать папку с документами"""
    if not os.path.exists(docs_dir):
        print(f"❌ Папка не найдена: {docs_dir}")
        return 0
    
    # Собираем все .md файлы
    files = [f for f in os.listdir(docs_dir) if f.endswith('.md')]
    if not files:
        print(f"❌ Нет .md файлов в {docs_dir}")
        return 0
    
    print(f"Найдено файлов: {len(files)}")
    
    # Удаляем старые документы клиента
    delete_client_docs(client_slug)
    
    # Обрабатываем каждый файл
    all_points = []
    point_id = abs(hash(client_slug)) % 100000000
    
    for filename in files:
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
        chunks = split_into_chunks(content, filename, doc_id, client_slug)
        print(f"  {filename}: {len(chunks)} chunks")
        
        for chunk in chunks:
            print(f"    Embedding: {chunk['metadata']['section_title'][:30]}...")
            vector = get_embedding(chunk["content"])
            all_points.append({
                "id": point_id,
                "vector": vector,
                "payload": chunk
            })
            point_id += 1
    
    if all_points:
        print(f"\nЗагружаю {len(all_points)} chunks в Qdrant...")
        result = upsert_to_qdrant(all_points)
        if result.get("status") == "ok":
            print(f"✅ Успешно загружено {len(all_points)} chunks")
        else:
            print(f"❌ Ошибка: {result}")
    
    return len(all_points)

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 sync_client.py <client_slug> [docs_folder]")
        print("Пример: python3 sync_client.py demo_salon ./demo_salon_docs")
        sys.exit(1)
    
    client_slug = sys.argv[1]
    
    # Папка с документами
    if len(sys.argv) >= 3:
        docs_dir = sys.argv[2]
    else:
        # По умолчанию ищем в ~/truffles/knowledge/<client_slug>
        docs_dir = f"/home/zhan/truffles/knowledge/{client_slug}"
    
    print(f"=" * 50)
    print(f"СИНХРОНИЗАЦИЯ: {client_slug}")
    print(f"Папка: {docs_dir}")
    print(f"=" * 50)
    
    total = sync_folder(client_slug, docs_dir)
    
    print(f"\n{'=' * 50}")
    print(f"ИТОГО: {total} chunks")
    print(f"{'=' * 50}")

if __name__ == "__main__":
    main()
