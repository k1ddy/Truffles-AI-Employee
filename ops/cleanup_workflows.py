#!/usr/bin/env python3
"""Cleanup unused workflows - identify and delete"""

import requests

API_KEY = 'REDACTED_JWT'

# Get all workflows
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']

# Workflows to KEEP (Truffles core + Gate projects)
KEEP_IDS = [
    # Truffles active
    '656fmXR6GPZrJbxm',  # 1_Webhook
    'HQOWuMDIBPphC86v',  # 9_Telegram_Callback
    'ZRcuYYCv1o9B0MyY',  # 10_Handover_Monitor
    'zTbaCLWLJN6vPMk4',  # Knowledge Sync
    
    # Truffles sub-workflows (called from webhook)
    'C38zCf2jfc2Zqfzf',  # 2_ChannelAdapter
    'DCs6AoJDIOPB4ZtF',  # 3_Normalize
    '3QqFRxapNa29jODD',  # 4_MessageBuffer
    'kEXEMbThwUsCJ2Cz',  # 5_TurnDetector
    '4vaEvzlaMrgovhNz',  # 6_Multi-Agent
    '7jGZrdbaAAvtTnQX',  # 7_Escalation_Handler
    'fFPEbTNlkBSjo66A',  # 8_Telegram_Adapter
    
    # Gate projects (other)
    'uplsVTCuGfH9Yafv',  # Gate Crypto v2
    '5Fo72obszME5y9q2',  # Gate GOLD exp1
    '9LukFnXTRJgsUuO2',  # Gate GOLD exp2 Gemini
]

print("=== WORKFLOWS TO KEEP ===")
keep_count = 0
for w in workflows:
    if w['id'] in KEEP_IDS:
        print(f"  KEEP: {w['name']} ({w['id']})")
        keep_count += 1

print(f"\n=== WORKFLOWS TO DELETE ({len(workflows) - keep_count}) ===")
to_delete = []
for w in workflows:
    if w['id'] not in KEEP_IDS:
        print(f"  DELETE: {w['name']} ({w['id']})")
        to_delete.append(w)

print(f"\nTotal: {len(workflows)} workflows")
print(f"Keep: {keep_count}")
print(f"Delete: {len(to_delete)}")

# Confirm before deleting
confirm = input("\nType 'DELETE' to confirm deletion: ")
if confirm == 'DELETE':
    for w in to_delete:
        resp = requests.delete(
            f"https://n8n.truffles.kz/api/v1/workflows/{w['id']}",
            headers={'X-N8N-API-KEY': API_KEY}
        )
        status = "OK" if resp.status_code == 200 else f"FAIL ({resp.status_code})"
        print(f"  Deleted {w['name']}: {status}")
    print("\nCleanup complete!")
else:
    print("\nCancelled. No workflows deleted.")
