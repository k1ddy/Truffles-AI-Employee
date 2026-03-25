# CRM Port v1

Purpose
- Standardize CRM integration without coupling core logic to a vendor.

Interface
- create_or_update_lead(request: LeadUpsertRequest) -> Result[LeadUpsertResult]
- log_interaction(request: InteractionLogRequest) -> Result[InteractionLogResult]

LeadUpsertRequest
- client_id: uuid
- branch_id: uuid | null
- external_id: string | null
- name: string | null
- phone: string | null
- email: string | null
- tags: list[string] | null
- source: string | null
- metadata: object

LeadUpsertResult
- lead_id: string
- external_id: string | null
- raw: object

InteractionLogRequest
- lead_id: string
- conversation_id: uuid | null
- channel: string
- content: string
- occurred_at: date-time
- metadata: object

InteractionLogResult
- interaction_id: string
- raw: object

Rules
- Idempotency supported via external_id or metadata.idempotency_key.
- Errors are returned as Result.fail with stable codes (CRM_TIMEOUT, CRM_REJECTED).

Notes
- Breaking changes require a new version file (crm_port.v2.md).
