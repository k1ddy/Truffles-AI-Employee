#!/usr/bin/env python3
"""
Add:
1. Pin message after escalation (Telegram Adapter)
2. Unpin after resolve (Callback)
3. Check delivery status
4. Delete "Отправлено" after 3 sec
"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"

# ============ TELEGRAM ADAPTER - Add Pin ============
print("=== TELEGRAM ADAPTER ===")
ADAPTER_ID = "fFPEbTNlkBSjo66A"

url = f"https://n8n.truffles.kz/api/v1/workflows/{ADAPTER_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    adapter = json.loads(response.read().decode())

# Add Pin Message node
pin_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Prepare Data').first().json.bot_token }}/pinChatMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Prepare Data').first().json.chat_id }}"},
                {"name": "message_id", "value": "={{ $('Send Escalation').first().json.result.message_id }}"},
                {"name": "disable_notification", "value": "=true"}
            ]
        },
        "options": {"ignore_errors": True}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1400, 300],
    "id": "adapter-pin-msg",
    "name": "Pin Escalation"
}

# Check if exists
exists = any(n['name'] == 'Pin Escalation' for n in adapter['nodes'])
if not exists:
    adapter['nodes'].append(pin_node)
    print("Added: Pin Escalation")

# Update connections: Send Escalation -> Pin Escalation -> Save Channel Refs
connections = adapter['connections']
if 'Send Escalation' in connections:
    connections['Send Escalation']['main'] = [[{"node": "Pin Escalation", "type": "main", "index": 0}]]
connections['Pin Escalation'] = {"main": [[{"node": "Save Channel Refs", "type": "main", "index": 0}]]}
print("Updated: Send Escalation -> Pin Escalation -> Save Channel Refs")

# Save adapter
update_payload = {
    "name": adapter["name"],
    "nodes": adapter["nodes"],
    "connections": connections,
    "settings": adapter.get("settings", {}),
}
url = f"https://n8n.truffles.kz/api/v1/workflows/{ADAPTER_ID}"
data = json.dumps(update_payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}, method='PUT')
with urllib.request.urlopen(req) as response:
    print(f"Updated: {json.loads(response.read().decode())['name']}")

# ============ CALLBACK - Add Unpin and improve confirm ============
print("\n=== TELEGRAM CALLBACK ===")
CALLBACK_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/workflows/{CALLBACK_ID}"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    callback = json.loads(response.read().decode())

# Add Unpin Message node (after resolve)
unpin_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/unpinChatMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [700, 450],
    "id": "cb-unpin-msg",
    "name": "Unpin Escalation"
}

# Add Check Delivery node
check_delivery_node = {
    "parameters": {
        "conditions": {
            "options": {"version": 2},
            "combinator": "and",
            "conditions": [{
                "id": "delivery-ok",
                "leftValue": "={{ $json.success }}",
                "rightValue": True,
                "operator": {"type": "boolean", "operation": "true"}
            }]
        }
    },
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.2,
    "position": [700, 600],
    "id": "cb-check-delivery",
    "name": "Delivery OK?"
}

# Add Delivery Failed node
delivery_failed_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Find Handover Data').first().json.bot_token }}/sendMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Parse Message').first().json.chat_id }}"},
                {"name": "message_thread_id", "value": "={{ $('Parse Message').first().json.topic_id }}"},
                {"name": "text", "value": "❌ Сообщение не доставлено клиенту"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [900, 700],
    "id": "cb-delivery-failed",
    "name": "Notify Delivery Failed"
}

# Add Delete Confirm node (delete "Отправлено" after delay)
delete_confirm_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Find Handover Data').first().json.bot_token }}/deleteMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Parse Message').first().json.chat_id }}"},
                {"name": "message_id", "value": "={{ $('Confirm Sent to Topic').first().json.result.message_id }}"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1200, 550],
    "id": "cb-delete-confirm",
    "name": "Delete Confirm Message"
}

# Wait node before delete
wait_node = {
    "parameters": {"amount": 3, "unit": "seconds"},
    "type": "n8n-nodes-base.wait",
    "typeVersion": 1.1,
    "position": [1100, 550],
    "id": "cb-wait-delete",
    "name": "Wait 3s",
    "webhookId": "wait-delete-confirm"
}

# Add nodes
for new_node in [unpin_node, check_delivery_node, delivery_failed_node, wait_node, delete_confirm_node]:
    exists = any(n['name'] == new_node['name'] for n in callback['nodes'])
    if not exists:
        callback['nodes'].append(new_node)
        print(f"Added: {new_node['name']}")

# Update Send Manager Reply to check success
for node in callback['nodes']:
    if node['name'] == 'Send Manager Reply to WhatsApp':
        # Add returnFullResponse to get status
        node['parameters']['options'] = {"response": {"response": {"fullResponse": True}}}
        print("Updated: Send Manager Reply (full response)")

# Fix Confirm Sent text
for node in callback['nodes']:
    if node['name'] == 'Confirm Sent to Topic':
        node['parameters']['bodyParameters']['parameters'][2]['value'] = "=✅ Доставлено"
        print("Updated: Confirm Sent (shorter text)")

# Update connections
connections = callback['connections']

# Remove Buttons Resolve -> Unpin Escalation -> Answer Callback
connections['Remove Buttons Resolve']['main'] = [[{"node": "Unpin Escalation", "type": "main", "index": 0}]]
connections['Unpin Escalation'] = {"main": [[{"node": "Answer Callback", "type": "main", "index": 0}]]}

# Send Manager Reply -> Check Delivery -> [ok] Save Message, [fail] Notify Failed
connections['Send Manager Reply to WhatsApp']['main'] = [[{"node": "Save Manager Message", "type": "main", "index": 0}]]

# Save Manager Message -> Confirm Sent -> Wait -> Delete
connections['Confirm Sent to Topic'] = {"main": [[{"node": "Wait 3s", "type": "main", "index": 0}]]}
connections['Wait 3s'] = {"main": [[{"node": "Delete Confirm Message", "type": "main", "index": 0}]]}

print("Updated connections")

# Save callback
update_payload = {
    "name": callback["name"],
    "nodes": callback["nodes"],
    "connections": connections,
    "settings": callback.get("settings", {}),
}
url = f"https://n8n.truffles.kz/api/v1/workflows/{CALLBACK_ID}"
data = json.dumps(update_payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}, method='PUT')
with urllib.request.urlopen(req) as response:
    print(f"Updated: {json.loads(response.read().decode())['name']}")

print("\nSUCCESS!")
