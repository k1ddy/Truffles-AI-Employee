#!/usr/bin/env python3
"""
Скрипт для обновления промпта через API.

Использование:
    python update_prompt.py --client truffles --file prompt.txt
    python update_prompt.py --client truffles --text "Ты консультант..."
    python update_prompt.py --client truffles --get  # посмотреть текущий
    
Требует: requests
"""

import argparse
import sys
import requests

API_URL = "http://localhost:8000"  # Локально
# API_URL = "https://api.truffles.kz"  # Продакшн


def get_prompt(client_slug: str) -> None:
    """Получить текущий промпт."""
    try:
        response = requests.get(f"{API_URL}/admin/prompt/{client_slug}")
        if response.status_code == 200:
            data = response.json()
            print(f"\n=== Промпт для {client_slug} ===\n")
            print(data["text"])
            print(f"\n=== Конец ({len(data['text'])} символов) ===\n")
        elif response.status_code == 404:
            print(f"Ошибка: клиент '{client_slug}' или промпт не найден")
            sys.exit(1)
        else:
            print(f"Ошибка: {response.status_code} - {response.text}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Ошибка: не удалось подключиться к {API_URL}")
        sys.exit(1)


def update_prompt(client_slug: str, text: str) -> None:
    """Обновить промпт."""
    # Валидация
    if not text or not text.strip():
        print("Ошибка: промпт не может быть пустым")
        sys.exit(1)
    
    if len(text) > 10000:
        print(f"Ошибка: промпт слишком длинный ({len(text)} > 10000)")
        sys.exit(1)
    
    # Подтверждение
    print(f"\n=== Новый промпт для {client_slug} ===\n")
    print(text[:500] + "..." if len(text) > 500 else text)
    print(f"\n=== {len(text)} символов ===\n")
    
    confirm = input("Применить? (y/n): ").strip().lower()
    if confirm != "y":
        print("Отменено")
        sys.exit(0)
    
    # Отправка
    try:
        response = requests.put(
            f"{API_URL}/admin/prompt/{client_slug}",
            json={"text": text}
        )
        if response.status_code == 200:
            print(f"✓ Промпт обновлён для {client_slug}")
        elif response.status_code == 404:
            print(f"Ошибка: клиент '{client_slug}' не найден")
            sys.exit(1)
        else:
            print(f"Ошибка: {response.status_code} - {response.text}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Ошибка: не удалось подключиться к {API_URL}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Управление промптами")
    parser.add_argument("--client", "-c", required=True, help="Slug клиента (truffles, demo_salon)")
    parser.add_argument("--get", "-g", action="store_true", help="Получить текущий промпт")
    parser.add_argument("--file", "-f", help="Файл с промптом")
    parser.add_argument("--text", "-t", help="Текст промпта")
    parser.add_argument("--api", default=API_URL, help="URL API")
    
    args = parser.parse_args()
    
    global API_URL
    API_URL = args.api
    
    if args.get:
        get_prompt(args.client)
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
            update_prompt(args.client, text)
        except FileNotFoundError:
            print(f"Ошибка: файл '{args.file}' не найден")
            sys.exit(1)
    elif args.text:
        update_prompt(args.client, args.text)
    else:
        print("Ошибка: укажите --get, --file или --text")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
