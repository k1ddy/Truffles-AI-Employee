# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - banner [ref=e3]:
      - generic [ref=e4]:
        - generic [ref=e5]:
          - heading "Truffles Console" [level=1] [ref=e6]
          - navigation [ref=e7]:
            - link "Заявки" [ref=e8] [cursor=pointer]:
              - /url: /
            - link "Записи" [ref=e9] [cursor=pointer]:
              - /url: /calendar
            - link "Статус" [ref=e10] [cursor=pointer]:
              - /url: /ops
            - link "Журнал" [ref=e11] [cursor=pointer]:
              - /url: /audit
            - link "Настройки" [ref=e12] [cursor=pointer]:
              - /url: /settings
        - generic [ref=e13]:
          - paragraph [ref=e14]: Вы вошли
          - button "Выйти" [ref=e15] [cursor=pointer]
    - main [ref=e16]:
      - generic [ref=e17]:
        - paragraph [ref=e18]: Не удалось загрузить заявки
        - button "Повторить" [ref=e19] [cursor=pointer]
  - button "Open Next.js Dev Tools" [ref=e25] [cursor=pointer]:
    - img [ref=e26]
  - alert [ref=e29]
```