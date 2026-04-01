-- Seed services and specialist_services from specialists.services

WITH service_rows AS (
    SELECT
        s.client_id,
        s.branch_id,
        (svc->>'name') AS name,
        NULLIF(svc->>'duration_min', '')::int AS duration_min,
        NULLIF(svc->>'price', '')::int AS price
    FROM specialists s
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(s.services, '[]'::jsonb)) AS svc
    WHERE s.services IS NOT NULL
)
INSERT INTO services (client_id, branch_id, name, duration_min, price)
SELECT DISTINCT ON (client_id, branch_id, name)
    client_id,
    branch_id,
    name,
    duration_min,
    price
FROM service_rows
WHERE name IS NOT NULL AND name <> ''
ON CONFLICT (client_id, branch_id, name) DO NOTHING;

WITH service_rows AS (
    SELECT
        s.id AS specialist_id,
        s.client_id,
        s.branch_id,
        (svc->>'name') AS name,
        NULLIF(svc->>'duration_min', '')::int AS duration_min,
        NULLIF(svc->>'price', '')::int AS price
    FROM specialists s
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(s.services, '[]'::jsonb)) AS svc
    WHERE s.services IS NOT NULL
)
INSERT INTO specialist_services (specialist_id, service_id, duration_min, price)
SELECT
    r.specialist_id,
    sv.id,
    r.duration_min,
    r.price
FROM service_rows r
JOIN services sv
  ON sv.client_id = r.client_id
 AND sv.branch_id = r.branch_id
 AND sv.name = r.name
ON CONFLICT DO NOTHING;

WITH hours AS (
    SELECT
        s.branch_id,
        day.key AS day,
        (day.value->>'start')::time AS start_time,
        (day.value->>'end')::time AS end_time
    FROM specialists s
    CROSS JOIN LATERAL jsonb_each(s.working_hours) AS day
    WHERE jsonb_typeof(day.value) = 'object'
),
agg AS (
    SELECT
        branch_id,
        day,
        min(start_time) AS start_time,
        max(end_time) AS end_time
    FROM hours
    GROUP BY branch_id, day
),
per_branch AS (
    SELECT
        branch_id,
        jsonb_object_agg(
            day,
            jsonb_build_object(
                'start', to_char(start_time, 'HH24:MI'),
                'end', to_char(end_time, 'HH24:MI')
            )
        ) AS working_hours
    FROM agg
    GROUP BY branch_id
)
UPDATE branches b
SET working_hours = COALESCE(pb.working_hours, b.working_hours)
FROM per_branch pb
WHERE b.id = pb.branch_id;
