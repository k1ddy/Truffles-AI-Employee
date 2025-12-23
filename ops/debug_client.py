#!/usr/bin/env python3
"""
Быстрая диагностика проблем клиента.
Usage: python3 debug_client.py +77015705555 [--limit 10]
"""
import subprocess
import json
import argparse
from datetime import datetime

def run_sql(query):
    """Execute SQL and return results"""
    cmd = f'''docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -t -A -F '|' -c "{query}"'''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}")
        return []
    
    rows = []
    for line in result.stdout.strip().split('\n'):
        if line:
            rows.append(line.split('|'))
    return rows

def format_phone(phone):
    """Normalize phone format"""
    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    if phone.startswith('8') and len(phone) == 11:
        phone = '7' + phone[1:]
    return phone

def main():
    parser = argparse.ArgumentParser(description="Debug client issues")
    parser.add_argument("phone", help="Client phone number")
    parser.add_argument("--limit", type=int, default=10, help="Number of messages")
    parser.add_argument("--traces", action="store_true", help="Show from traces table")
    args = parser.parse_args()
    
    phone = format_phone(args.phone)
    
    print(f"\n{'='*70}")
    print(f"DEBUG: {phone}")
    print(f"{'='*70}")
    
    # First try traces table
    if args.traces:
        print("\n📊 FROM message_traces:")
        traces = run_sql(f"""
            SELECT 
                to_char(created_at, 'MM-DD HH24:MI'),
                intent,
                ROUND(rag_top_score::numeric, 2),
                rag_top_doc,
                CASE WHEN needs_escalation THEN '🚨' ELSE '' END,
                LEFT(message, 40),
                LEFT(response, 50)
            FROM message_traces 
            WHERE phone LIKE '%{phone}%'
            ORDER BY created_at DESC 
            LIMIT {args.limit}
        """)
        
        if traces:
            print(f"{'Time':<12} {'Intent':<15} {'Score':<6} {'Doc':<12} {'Esc':<3} Message → Response")
            print("-" * 100)
            for t in traces:
                if len(t) >= 7:
                    print(f"{t[0]:<12} {t[1]:<15} {t[2]:<6} {t[3]:<12} {t[4]:<3} {t[5]} → {t[6]}")
        else:
            print("No traces found. Traces table may be empty (workflow not updated yet).")
    
    # Get from messages table (always works)
    print("\n💬 RECENT MESSAGES:")
    messages = run_sql(f"""
        SELECT 
            to_char(m.created_at, 'MM-DD HH24:MI'),
            m.role,
            LEFT(m.content, 80)
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE u.phone LIKE '%{phone}%'
        ORDER BY m.created_at DESC
        LIMIT {args.limit * 2}
    """)
    
    if messages:
        for m in reversed(messages):
            if len(m) >= 3:
                role = "👤" if m[1] == 'user' else "🤖"
                print(f"{m[0]} {role} {m[2]}")
    else:
        print("No messages found for this phone.")
    
    # Get conversation info
    print("\n📋 CONVERSATION INFO:")
    conv = run_sql(f"""
        SELECT 
            c.id,
            c.escalated_at,
            u.phone,
            (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as msg_count
        FROM conversations c
        JOIN users u ON c.user_id = u.id
        WHERE u.phone LIKE '%{phone}%'
        ORDER BY u.created_at DESC
        LIMIT 1
    """)
    
    if conv and conv[0]:
        c = conv[0]
        print(f"  Conversation ID: {c[0]}")
        print(f"  Phone: {c[2]}")
        print(f"  Message count: {c[3]}")
        print(f"  Escalated at: {c[1] if c[1] else 'Never'}")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
