#!/usr/bin/env python3
"""Get Telegram chat_id from bot updates"""
import json
import urllib.request
import sys

tokens = [
    ("TrufflesChatBot", "REDACTED_TELEGRAM_BOT_TOKEN"),
    ("DemoSalonBot", "REDACTED_TELEGRAM_BOT_TOKEN"),
]

for name, token in tokens:
    print(f"\n=== {name} ===")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        if not data.get("ok"):
            print(f"Error: {data}")
            continue
            
        updates = data.get("result", [])
        if not updates:
            print("No updates")
            continue
        
        seen_chats = set()
        for u in updates[-20:]:
            msg = u.get("message") or u.get("my_chat_member", {})
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            title = chat.get("title", "")
            chat_type = chat.get("type", "")
            
            if chat_id and chat_id not in seen_chats:
                seen_chats.add(chat_id)
                text = ""
                if "message" in u and "text" in u["message"]:
                    text = u["message"]["text"][:50]
                print(f"chat_id: {chat_id} | type: {chat_type} | title: {title} | text: {text}")
                
    except Exception as e:
        print(f"Error: {e}")
