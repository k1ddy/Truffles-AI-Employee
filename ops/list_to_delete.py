#!/usr/bin/env python3
"""List workflows to delete (no action)"""

import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']

# Workflows to KEEP
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

print("=== KEEP ===")
for w in workflows:
    if w['id'] in KEEP_IDS:
        print(f"  {w['name']}")

print("\n=== DELETE ===")
to_delete = []
for w in workflows:
    if w['id'] not in KEEP_IDS:
        print(f"  {w['name']}")
        to_delete.append(w['id'])

print(f"\nKeep: {len(KEEP_IDS)}, Delete: {len(to_delete)}")
