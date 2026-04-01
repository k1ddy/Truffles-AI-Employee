# Inbox UX Standard — Analysis + Variants

**Date:** 2026-01-30  
**Scope:** Inbox (Cases) UX: scanability, chat context, quick actions, consultant info, diagnostics separation, and cross-tab clarity.  
**Sources:** `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `console-web/src/components/*` (InboxView/CaseList/CaseConversation/CaseDetailsPanel/ChatInterface/InboxMacros).

---

## 1) Current state (code-backed)

**Layout:** 3-pane grid — list (left), conversation (center), details (right).  
**List:** search + status/sort + assigned + advanced filters; compact cards with name/phone, preview, SLA, tags (NEW/LIVE/⚠️).  
**Conversation:** header (case id, SLA, status, channel/trigger), actions (take/resolve), chat + input.  
**Details:** collapsible cards (Context, Health, Explain, Trace, Telegram).  
**Quick replies:** static macros in a separate card under conversation.

---

## 2) UX friction (operator view)

1) **Scan noise in list + filters.** Filters dominate the left column; advanced toggles + search reduce the signal from the queue itself.
2) **Quick actions and quick replies are split.** Actions (take/resolve) are in header; macros are detached under chat, reducing speed.
3) **Details mix operator info with diagnostics.** Explain/Trace share the same visible hierarchy as context/health; operators see technical fields too early.
4) **Chat context is present but not focal.** Context summary is in the right column; the center (chat) lacks a pinned summary, so operators switch focus to read context.
5) **Cross-tab confusion risk.** The page uses “Inbox” title while navigation uses “Заявки”; diagnostics content feels like Ops/Debug.

---

## 3) UX goals (standard principles)

- **One screen = one job:** Inbox is for handling cases and replying; anything diagnostic lives behind a clear “Diagnostics” gate.
- **Priority order:** Action → Conversation → Context → Diagnostics.
- **Fast scanning:** list shows the minimal signals to decide what to open next.
- **Operator language:** user-facing text in RU; technical terms only inside Diagnostics.
- **No cross-tab bleed:** Inbox does not edit knowledge, team, or settings.

---

## 4) Variants for the main Inbox page

### Variant A — 3‑pane “Operator Command” (desktop standard)
**Layout:** List (left) + Chat (center) + Details (right).  
**Details panel:** default tabs: “Контекст” + “Заявка” + “Консультант”; “Диагностика” hidden behind a separate tab.  
**Quick replies:** inline chips above composer or right beside it; grouped by “Системные/Клиентские”.

**Pros:** Maximum visibility; minimal navigation; best for high volume.  
**Cons:** Needs strict hierarchy to avoid noise.

### Variant B — 2‑pane + slide‑out details
**Layout:** List (left) + Chat (right). Details open as a right drawer or top tab row (“Контекст/Заявка/Диагностика”).  
**Quick replies:** anchored near composer.

**Pros:** Cleaner; easier learning curve.  
**Cons:** Extra click for details; harder for supervisors who need health + context at a glance.

### Variant C — Single column (compact / mobile)
**Layout:** Tabs across top: “Очередь / Чат / Контекст / Диагностика”.  
**Quick replies:** sticky row above input; macros condensed.

**Pros:** Works on small screens; low noise.  
**Cons:** Slow for power users; more switching.

---

## 5) Recommended standard (A + responsive rules)

**Standard choice:** Variant A for desktop, auto‑degrading to Variant B/C on smaller widths.

### 5.1 Layout & hierarchy
- **Left (Queue):** compact list with sticky filters header; list scrolls independently.
- **Center (Chat):** primary workspace; include a **mini context strip** at top (last user intent + last inbound time).
- **Right (Details):** organized into clear cards; diagnostics in a separate tab.

### 5.2 List (Queue) standard
- **Visible fields:** name/phone, last message preview, last activity, SLA badge, tags (NEW/LIVE/⚠️), branch (only when multi‑branch & no global selection).
- **Default sorting:** activity; quick toggles for “Мои” and “Срочные”.
- **Advanced filters:** hidden; branch filter only when global context is “All”.

### 5.3 Chat + actions standard
- **Action bar:** “Взять”, “Закрыть”, “Передать” (if allowed) + small status badges.
- **Quick replies:** chips above composer; full macros list in a compact drawer.
- **Input hints:** show service + time prompts when case is pending (operator guidance only).

### 5.4 Details (Context + Case + Consultant)
**Default tabs:**
- **Контекст:** клиент, телефон, краткая сводка, причина обращения.
- **Заявка:** статус, SLA, канал, время входящего/исходящего, флаги доставки.
- **Консультант:** assigned manager (имя/роль), статус работы (взял/не взял), первый ответ/закрытие (если доступно из API).

**Diagnostics tab (hidden by default):** Explain + Trace + Telegram trail. Visible for support/admin roles only.

### 5.5 Cross‑tab clarity
- **Inbox ≠ Knowledge/Team/Settings:** no editing knowledge, no team management actions here.
- **Naming:** “Заявки” as primary label; “Inbox” only in tech references.
- **Diagnostics gating:** belongs to Ops mindset; never default for managers.

---

## 6) Suggested success criteria (UX)

- Оператор понимает статус заявки за 3–5 секунд (без открытия деталей).
- Быстрые ответы доступны без скролла, рядом с полем ввода.
- Диагностика не мешает обработке (скрыта, явный вход).
- Ясно, где “работать с заявкой”, и где “настраивать систему”.

---

## 7) V3 applied changes (2026-01-30)

- Chat‑first layout widened (Inbox uses wider max‑width, narrower side columns).
- Quick replies now live next to composer with chips + full list + search + manage tabs.
- Details tabs clarified with RU labels; channel/trigger mapped to human‑friendly labels.
