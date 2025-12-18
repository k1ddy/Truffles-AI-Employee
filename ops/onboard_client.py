#!/usr/bin/env python3
"""
Онбординг нового клиента.

Использование:
  python3 onboard_client.py

Скрипт спросит все параметры интерактивно.
"""
import subprocess
import sys

def run_sql(sql):
    """Выполнить SQL запрос"""
    result = subprocess.run([
        'docker', 'exec', '-i', 'truffles_postgres_1',
        'psql', '-U', 'n8n', '-d', 'chatbot'
    ], input=sql, capture_output=True, text=True)
    return result.stdout, result.stderr

def escape_sql(text):
    """Экранировать текст для SQL"""
    return text.replace("'", "''")

def main():
    print("=" * 50)
    print("ОНБОРДИНГ НОВОГО КЛИЕНТА")
    print("=" * 50)
    
    # 1. Базовые данные
    print("\n[1/5] БАЗОВЫЕ ДАННЫЕ\n")
    
    slug = input("Slug (латиница, например 'beauty_salon'): ").strip()
    if not slug:
        print("Ошибка: slug обязателен")
        sys.exit(1)
    
    business_name = input("Название бизнеса (например 'Салон красоты Мира'): ").strip()
    business_type = input("Тип бизнеса [salon/shop/service]: ").strip() or "salon"
    
    # 2. WhatsApp (ChatFlow)
    print("\n[2/5] WHATSAPP (CHATFLOW)\n")
    
    instance_id = input("Instance ID (из ChatFlow): ").strip()
    phone = input("Номер бота (например +77001234567): ").strip()
    
    # 3. Google Drive
    print("\n[3/5] GOOGLE DRIVE\n")
    
    folder_id = input("Folder ID (из URL папки): ").strip()
    
    # 4. Эскалация
    print("\n[4/5] ЭСКАЛАЦИЯ\n")
    
    escalation_phone = input("Телефон менеджера для эскалации: ").strip()
    escalation_name = input("Имя менеджера: ").strip() or "Менеджер"
    
    # 5. Контакты бизнеса (для промпта)
    print("\n[5/5] КОНТАКТЫ БИЗНЕСА (для промпта)\n")
    
    address = input("Адрес: ").strip()
    work_hours = input("Часы работы (например '9:00-21:00'): ").strip() or "9:00-21:00"
    contact_phone = input("Телефон для клиентов: ").strip() or phone
    
    # Генерируем промпт
    if business_type == "salon":
        prompt_template = f'''# {business_name} — AI-помощник

Ты — помощник {business_name}. Отвечаешь на вопросы клиентов в WhatsApp.

## Твои задачи:
1. Отвечать на вопросы об услугах и ценах
2. Помогать с записью (собираешь заявку, передаёшь администратору)
3. Отвечать на частые вопросы
4. Обрабатывать возражения мягко и профессионально

## Как общаться:
- Коротко и по делу (2-4 предложения)
- Дружелюбно, но профессионально
- Если не знаешь точный ответ — честно скажи и предложи связаться с администратором
- Не выдумывай цены и услуги которых нет в базе знаний
- Если вопрос не про салон/услуги/запись — мягко верни к теме салона

## Запись на услугу:
Ты НЕ записываешь напрямую. Собери:
1. Какая услуга
2. Желаемая дата и время
3. Имя клиента
После скажи: "Передал администратору, вам перезвонят для подтверждения."

## Контакты:
- Адрес: {address}
- Телефон: {contact_phone}
- Часы работы: {work_hours}

## Нельзя:
- Давать скидки без согласования
- Обсуждать конкурентов
- Давать медицинские советы
- Обсуждать темы не связанные с бизнесом'''
    else:
        prompt_template = f'''# {business_name} — AI-помощник

Ты — помощник {business_name}. Отвечаешь на вопросы клиентов в WhatsApp.

## Как общаться:
- Коротко и по делу (2-4 предложения)
- Дружелюбно, но профессионально
- Если не знаешь — честно скажи

## Контакты:
- Адрес: {address}
- Телефон: {contact_phone}
- Часы работы: {work_hours}'''

    # Показываем что будет создано
    print("\n" + "=" * 50)
    print("ПРОВЕРЬТЕ ДАННЫЕ:")
    print("=" * 50)
    print(f"""
Slug: {slug}
Бизнес: {business_name}
Instance ID: {instance_id}
Телефон бота: {phone}
Google Drive: {folder_id}
Эскалация: {escalation_name} ({escalation_phone})

Webhook URL:
https://n8n.truffles.kz/webhook/a29b2ad2-9485-476c-897d-34799c3f940b/{slug}
""")
    
    confirm = input("\nВсё верно? [y/n]: ").strip().lower()
    if confirm != 'y':
        print("Отменено.")
        sys.exit(0)
    
    # Создаём записи в БД
    print("\nСоздаю записи в БД...")
    
    # 1. clients
    config = {
        "folder_id": folder_id,
        "instance_id": instance_id,
        "phone": phone,
        "escalation_phone": escalation_phone,
        "escalation_name": escalation_name,
        "business_name": business_name
    }
    
    import json
    config_json = json.dumps(config, ensure_ascii=False)
    
    sql_client = f"""
INSERT INTO clients (name, status, config)
VALUES ('{escape_sql(slug)}', 'active', '{escape_sql(config_json)}'::jsonb)
ON CONFLICT (name) DO UPDATE SET 
  config = EXCLUDED.config,
  status = 'active';
"""
    
    out, err = run_sql(sql_client)
    if err and 'ERROR' in err:
        print(f"Ошибка clients: {err}")
    else:
        print("✓ clients")
    
    # 2. prompts
    sql_prompt = f"""
INSERT INTO prompts (client_id, name, text)
SELECT c.id, 'system', '{escape_sql(prompt_template)}'
FROM clients c WHERE c.name = '{escape_sql(slug)}'
ON CONFLICT (client_id, name) DO UPDATE SET text = EXCLUDED.text;
"""
    
    out, err = run_sql(sql_prompt)
    if err and 'ERROR' in err:
        print(f"Ошибка prompts: {err}")
    else:
        print("✓ prompts")
    
    # Итог
    print("\n" + "=" * 50)
    print("ГОТОВО!")
    print("=" * 50)
    print(f"""
Следующие шаги:

1. В ChatFlow укажи webhook URL:
   https://n8n.truffles.kz/webhook/a29b2ad2-9485-476c-897d-34799c3f940b/{slug}

2. Загрузи документы в Google Drive папку:
   https://drive.google.com/drive/folders/{folder_id}
   
   Нужные файлы:
   - services.md (услуги и цены)
   - faq.md (частые вопросы)
   - objections.md (работа с возражениями)
   - rules.md (правила бота)

3. Запусти синхронизацию базы знаний:
   python3 sync_client.py {slug}

4. Протестируй — напиши на номер {phone}
""")

if __name__ == "__main__":
    main()
