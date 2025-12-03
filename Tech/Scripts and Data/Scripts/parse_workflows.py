import json

with open(r'C:\Users\user\Downloads\TrufflesDocs\workflows_list.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

workflows = data.get('data', [])
print(f"Total workflows: {len(workflows)}\n")

for w in workflows:
    print(f"{w['id']} - {w['name']}")
