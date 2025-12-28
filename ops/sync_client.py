#!/usr/bin/env python3
"""
Синхронизация базы знаний одного клиента.

Использование:
  python3 sync_client.py <client_slug> [docs_folder] [--validate] [--validate-only]

Примеры:
  python3 sync_client.py demo_salon
  python3 sync_client.py demo_salon /path/to/docs
  python3 sync_client.py demo_salon --validate-only
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

import requests
import yaml

# === КОНФИГ ===
def _resolve_docker_ip(container_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    ip = result.stdout.strip()
    return ip or None


BGE_URL = os.environ.get("BGE_M3_URL")
if not BGE_URL:
    bge_ip = _resolve_docker_ip("bge-m3")
    BGE_URL = f"http://{bge_ip}:80/embed" if bge_ip else "http://bge-m3:80/embed"

QDRANT_URL = os.environ.get("QDRANT_URL")
if not QDRANT_URL:
    qdrant_ip = _resolve_docker_ip("truffles_qdrant_1")
    QDRANT_URL = f"http://{qdrant_ip}:6333" if qdrant_ip else "http://qdrant:6333"
QDRANT_COLLECTION = "truffles_knowledge"
QDRANT_API_KEY = (
    os.environ.get("QDRANT_API_KEY")
    or os.environ.get("QDRANT__SERVICE__API_KEY")
    or "REDACTED_PASSWORD"
)
QDRANT_API_KEY = QDRANT_API_KEY.strip()

_REQUIRED_CLIENT_PACK_FIELDS = [
    "client_pack.salon.name",
    "client_pack.salon.city",
    "client_pack.salon.address.full",
    "client_pack.salon.hours.days",
    "client_pack.salon.hours.open",
    "client_pack.salon.hours.close",
    "client_pack.salon.services_summary",
    "client_pack.salon.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.price_list",
]

_MISSING = object()


def _get_nested_value(data: dict, path: str):
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return _MISSING
        current = current[key]
    return current


def _is_empty_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _truth_path(client_slug: str) -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(
        repo_root,
        "truffles-api",
        "app",
        "knowledge",
        client_slug,
        "SALON_TRUTH.yaml",
    )


def validate_client_pack(truth_path: str) -> bool:
    if not os.path.exists(truth_path):
        print(f"❌ SALON_TRUTH.yaml не найден: {truth_path}")
        return False
    with open(truth_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        print(f"❌ Некорректный формат YAML: {truth_path}")
        return False

    missing = []
    for path in _REQUIRED_CLIENT_PACK_FIELDS:
        value = _get_nested_value(data, path)
        if value is _MISSING or _is_empty_value(value):
            missing.append(path)

    if missing:
        print("❌ client_pack: отсутствуют обязательные поля")
        for path in missing:
            print(f"  - {path}")
        return False

    print("✅ client_pack валиден")
    return True

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
    parser = argparse.ArgumentParser(description="Синхронизация базы знаний одного клиента.")
    parser.add_argument("client_slug", help="Slug клиента, например demo_salon")
    parser.add_argument("docs_folder", nargs="?", help="Папка с .md файлами (по умолчанию knowledge/<slug>)")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Проверить обязательные поля client_pack перед синхронизацией",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Только проверить client_pack и выйти без синхронизации",
    )
    args = parser.parse_args()

    client_slug = args.client_slug

    # Папка с документами
    if args.docs_folder:
        docs_dir = args.docs_folder
    else:
        # По умолчанию ищем в ~/truffles/knowledge/<client_slug>
        docs_dir = f"/home/zhan/truffles-main/knowledge/{client_slug}"

    if args.validate or args.validate_only:
        truth_path = _truth_path(client_slug)
        if not validate_client_pack(truth_path):
            sys.exit(2)
        if args.validate_only:
            return

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
