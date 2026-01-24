-- Backfill appointments from legacy bookings (idempotent)

INSERT INTO appointments (
    id,
    client_id,
    branch_id,
    specialist_id,
    user_id,
    conversation_id,
    status,
    source,
    confirmation_policy,
    start_at,
    end_at,
    customer_name,
    customer_phone,
    notes,
    version,
    created_by,
    created_at,
    updated_at
)
SELECT
    b.id,
    b.client_id,
    COALESCE(b.branch_id, s.branch_id) AS branch_id,
    b.specialist_id,
    c.user_id,
    b.conversation_id,
    CASE b.status
        WHEN 'pending' THEN 'PENDING_CONFIRMATION'
        WHEN 'confirmed' THEN 'CONFIRMED'
        WHEN 'cancelled' THEN 'CANCELLED'
        WHEN 'completed' THEN 'COMPLETED'
        WHEN 'no_show' THEN 'NO_SHOW'
        ELSE 'CONFIRMED'
    END AS status,
    'system' AS source,
    'manager' AS confirmation_policy,
    b.start_at,
    b.end_at,
    b.customer_name,
    b.customer_phone,
    b.notes,
    COALESCE(b.version, 1) AS version,
    b.created_by,
    COALESCE(b.created_at, now()),
    COALESCE(b.updated_at, now())
FROM bookings b
LEFT JOIN specialists s ON s.id = b.specialist_id
LEFT JOIN conversations c ON c.id = b.conversation_id
WHERE COALESCE(b.branch_id, s.branch_id) IS NOT NULL
ON CONFLICT (id) DO NOTHING;

INSERT INTO appointment_services (
    appointment_id,
    service_id,
    service_name,
    duration_min,
    price,
    buffer_before_min,
    buffer_after_min,
    created_at
)
SELECT
    b.id AS appointment_id,
    NULL AS service_id,
    b.service_type,
    COALESCE(b.service_duration_min, (EXTRACT(EPOCH FROM (b.end_at - b.start_at)) / 60)::int),
    b.service_price,
    0,
    0,
    COALESCE(b.created_at, now())
FROM bookings b
WHERE b.service_type IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO appointment_sync_states (
    appointment_id,
    provider,
    external_id,
    state,
    last_synced_at,
    created_at,
    updated_at
)
SELECT
    b.id AS appointment_id,
    'google_calendar' AS provider,
    b.google_event_id AS external_id,
    CASE b.google_sync_status
        WHEN 'synced' THEN 'OK'
        WHEN 'failed' THEN 'FAILED'
        ELSE 'PENDING'
    END AS state,
    b.updated_at AS last_synced_at,
    COALESCE(b.created_at, now()),
    COALESCE(b.updated_at, now())
FROM bookings b
WHERE b.google_event_id IS NOT NULL
ON CONFLICT (appointment_id, provider) DO NOTHING;
