#!/usr/bin/env python3
"""Delete unused workflows"""

import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']

KEEP_IDS = [
    '656fmXR6GPZrJbxm',  # 1_Webhook
    'HQOWuMDIBPphC86v',  # 9_Telegram_Callback
    'ZRcuYYCv1o9B0MyY',  # 10_Handover_Monitor
    'zTbaCLWLJN6vPMk4',  # Knowledge Sync
    'C38zCf2jfc2Zqfzf',  # 2_ChannelAdapter
    'DCs6AoJDIOPB4ZtF',  # 3_Normalize
    '3QqFRxapNa29jODD',  # 4_MessageBuffer
    'kEXEMbThwUsCJ2Cz',  # 5_TurnDetector
    '4vaEvzlaMrgovhNz',  # 6_Multi-Agent
    '7jGZrdbaAAvtTnQX',  # 7_Escalation_Handler
    'fFPEbTNlkBSjo66A',  # 8_Telegram_Adapter
    'uplsVTCuGfH9Yafv',  # Gate Crypto v2
    '5Fo72obszME5y9q2',  # Gate GOLD exp1
    '9LukFnXTRJgsUuO2',  # Gate GOLD exp2 Gemini
]

deleted = 0
failed = 0

for w in workflows:
    if w['id'] not in KEEP_IDS:
        resp = requests.delete(
            f"https://n8n.truffles.kz/api/v1/workflows/{w['id']}",
            headers={'X-N8N-API-KEY': API_KEY}
        )
        if resp.status_code == 200:
            print(f"  Deleted: {w['name']}")
            deleted += 1
        else:
            print(f"  FAILED: {w['name']} ({resp.status_code})")
            failed += 1

print(f"\nDeleted: {deleted}, Failed: {failed}")
