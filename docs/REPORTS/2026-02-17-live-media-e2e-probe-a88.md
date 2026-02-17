# Live Media E2E Probe (2026-02-17, a88)

Goal: verify claim `photo reference -> manager relay -> Console Plane media context -> Telegram manager context` with one short canonical probe (no long quality reruns).

## Scope

- Client: `demo_salon`
- Endpoint: `POST /webhook/demo_salon`
- JID: `77000000002@s.whatsapp.net` (allowlist)
- Branch instance: `b7f75692-951e-421a-aae6-f5db97394799`
- Runs:
  - `live-media-e2e-20260217-051948-sec` (2-step, no reset)
  - `live-media-e2e-20260217-052152-reset` (reset + 2-step canonical)

## Canonical run (`live-media-e2e-20260217-052152-reset`)

- `LIVE-MEDIA-E2E-1771287712-RESET` -> HTTP `200`
- `LIVE-MEDIA-E2E-1771287712-IMG` -> HTTP `200`
- `LIVE-MEDIA-E2E-1771287712-TXT` -> HTTP `200`

Probe artifacts:

- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/run_meta.json`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/response_reset.json`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/response_img.json`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/response_txt.json`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/messages_table.txt`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/handover_table.txt`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/outbox_table.txt`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/media_fields.tsv`
- `/tmp/booking_quality/live-media-e2e-20260217-052152-reset/media_file_ls_container.txt`

## Evidence summary

1. Inbound media persisted with Console-visible media fields:
- `messages.metadata.media.storage_path` present:
  `/home/zhan/truffles-media/demo_salon/d9d1d29d-e082-4c04-8c38-bb68093013f2/LIVE-MEDIA-E2E-1771287712-IMG.png`
- `messages.metadata.media.public_url` present:
  `https://api.truffles.kz/media/demo_salon/.../LIVE-MEDIA-E2E-1771287712-IMG.png?...`
- `messages.metadata.media.expires_at` present:
  `2026-02-17T01:22:04+00:00`
- File exists inside runtime container:
  `-rw-r--r-- ... LIVE-MEDIA-E2E-1771287712-IMG.png`

2. Escalation to manager happened on follow-up text:
- `message_id=LIVE-MEDIA-E2E-1771287712-TXT`
- `decision_meta.action=escalate`
- `decision_meta.source=llm_policy_core`
- handover created:
  `id=d0de04f2-7445-45f0-938b-d7f442d3eb40`, `status=pending`, `telegram_message_id=10429`

3. Outbound to client failed for all probe steps:
- `outbox_messages.status=FAILED`
- `last_error=[CHATFLOW_BILLING_BLOCKED] ChatFlow billing blocked: plan renewal required`
- affects `RESET`, `IMG`, `TXT` inbound ids in same run

4. Media relay completeness is still not proven:
- `messages.metadata.media.forwarded_to_telegram` is empty for probe image row.
- `style_reference_pending` remains in conversation context after escalation.
- No DB evidence that the same image was attached to manager-facing Telegram message in this run.

## Binary verdict for the claim

- `Inbound media stored + signed URL in Console context`: **YES**
- `Manager escalation created with Telegram message id`: **YES**
- `Client-facing reply delivery`: **NO** (billing-blocked outbox)
- `Same image guaranteed in manager Telegram + full context`: **NO (not proven in evidence)**

Overall claim `photo relay end-to-end fully works` is **NOT CONFIRMED**.

## Root blockers

1. Provider billing gate blocks outbox delivery (`CHATFLOW_BILLING_BLOCKED`).
2. Media relay path is not deterministic for style-reference handoff in this conversation:
   escalation happened via `llm_policy_core`, while `style_reference_pending` remained.
3. No hard proof binding handover telegram notification with the exact stored media object for this run.

## Minimal next fix scope (no system rewrite)

1. Add hard post-condition for media handoff:
   if `style_reference_pending.media` exists and action escalates, require `media_forwarded=true` marker in `decision_meta` + trace.
2. Persist handover media binding:
   store `handover.meta.media_refs[]` with `message_id`, `storage_path`, `public_url`, `sha256`.
3. Keep provider outage explicit:
   when outbox fails with billing/code, mark run as `transport_blocked` and block claim confirmation automatically.
