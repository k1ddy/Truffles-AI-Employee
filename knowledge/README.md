# База знаний

Здесь хранится контент для RAG.

## Канон

- Для конкретного клиента канон RAG = `knowledge/<client_slug>/` (например, `knowledge/demo_salon/`).
- Runtime pack (truth/policy/eval) живет в `truffles-api/app/knowledge/<client_slug>/`.

## Корневые файлы

- `faq.md`, `facts.md`, `examples.md`, `cases.md`, `objections.md`, `slang.md` — шаблоны/примеры.
- Эти файлы не участвуют в рантайме, пока не перенесены в `knowledge/<client_slug>/`.

## Принцип

Качество базы знаний = качество ответов. Структурировать чётко.
