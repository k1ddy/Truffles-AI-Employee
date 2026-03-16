# Knowledge Activation Release Runbook

## Purpose
Операционный SOP для deploy/canary/rollback dedicated knowledge activation worker/service после P5.

## Scope
- `truffles-knowledge-activation` worker
- `truffles-knowledge-activation-service`
- activation health in `/admin/health/check`
- activation gauges in `/metrics`
- CI post-deploy proof artifacts (`release_guard` + optional tenant closeout)

## Preconditions
- P3/P4 code already deployed in target image.
- `KNOWLEDGE_ACTIVATION_SERVICE_TOKEN` доступен в runtime env, если process endpoint защищен токеном.
- Есть image ref/digest для target release и previous rollback image.

## Canonical Deploy
```bash
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main \
PULL_IMAGE=1 \
RUN_MIGRATIONS=1 \
MIGRATION_BOOTSTRAP_MODE=auto \
REQUIRE_GHCR=1 \
VERIFY_VERSION=1 \
EXPECTED_GIT_COMMIT=<sha> \
EXPECTED_VERSION=main \
RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1 \
KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1 \
RUN_KNOWLEDGE_ACTIVATION_CANARY=1 \
KNOWLEDGE_ACTIVATION_CANARY_OUTPUT=/tmp/knowledge_activation_release_guard.json \
bash /home/zhan/truffles-main/scripts/restart_release.sh"
```

On merged `main`, `.github/workflows/ci.yml` now automates the same proof path:
1. deploy restarts API + workers + `truffles-knowledge-activation-service`
2. `scripts/knowledge_activation_postdeploy.sh` runs the P5 `release_guard`, optionally runs tenant closeout when explicit closeout target config is present, and emits `manifest.json` + `summary.md`
4. GitHub Actions uploads `knowledge-activation-proof` artifacts

## What The Release Command Must Prove
1. `restart_release.sh` restarts API + workers and, when `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1`, also restarts `truffles-knowledge-activation-service`.
2. Image parity includes API, workers, and activation service.
3. `truffles-api/scripts/knowledge_activation_release_guard.py` writes a JSON artifact with `decision=go|no_go`.

## Guard Signals (`go` only if all are true)
1. `service_health.payload.status == ok`
2. `service_health.payload.knowledge_activation_enabled == true`
3. `process_probe.status_code == 200`
4. `admin_health.knowledge_activation.status` is not above allowed threshold (default `warning`)
5. `metrics.snapshot.missing == []`

## Read Artifact
```bash
ssh -p 222 zhan@5.188.241.234 "cat /tmp/knowledge_activation_release_guard.json"
```

## Tenant Closeout Artifact
After the P5 guard is `go`, capture one tenant-aware closeout verdict for the rollout branch:
```bash
ssh -p 222 zhan@5.188.241.234 "python3 /home/zhan/truffles-main/ops/knowledge_activation_closeout.py \
--client-slug <client-slug> \
--branch-slug <branch-slug> \
--guard-json /tmp/knowledge_activation_release_guard.json \
--output /tmp/knowledge_activation_closeout.json \
--pretty"
```

The closeout artifact adds:
- `tenant.feature_enabled`
- `tenant.preview_available`
- `tenant.can_verify_now`
- `tenant.live_activation_status`
- `invariants.live_pointer_separated_from_pending_candidate`
- `invariants.ready_candidate_is_active`

`GO` for final closeout requires both:
1. P5 guard artifact `decision=go`
2. closeout artifact `decision=go`

## CI Closeout Configuration
`main` deploy automation resolves the tenant closeout target from explicit CI config:
- workflow-dispatch inputs:
  - `knowledge_activation_closeout_client_slug`
  - `knowledge_activation_closeout_branch_slug`
- or repository variables:
  - `KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG`
  - `KNOWLEDGE_ACTIVATION_CLOSEOUT_BRANCH_SLUG`

If neither source is configured, CI still runs the guard and uploads a truthful proof artifact with:
- `closeout.status = skipped`
- `closeout.reason = closeout_target_not_configured`

This is intentional until a dedicated consultant-verification canary tenant/env is provisioned.

Expected top-level fields:
- `captured_at`
- `decision`
- `reasons[]`
- `service_health`
- `process_probe`
- `admin_health`
- `metrics`

## Go / No-Go
- `GO`: artifact `decision=go`
- `NO_GO`: artifact `decision=no_go` or release script exits non-zero

Typical no-go reasons:
- `service_health_unavailable`
- `service_not_enabled`
- `process_probe_failed`
- `activation_health_critical`
- `metrics_unavailable`
- `activation_metrics_missing`

## Fast Rollback
Use the same release path with the previous digest/image.

```bash
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=<previous-digest> \
PULL_IMAGE=1 \
RUN_MIGRATIONS=1 \
MIGRATION_BOOTSTRAP_MODE=auto \
REQUIRE_GHCR=1 \
VERIFY_VERSION=1 \
RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1 \
KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1 \
RUN_KNOWLEDGE_ACTIVATION_CANARY=1 \
KNOWLEDGE_ACTIVATION_CANARY_OUTPUT=/tmp/knowledge_activation_release_guard.rollback.json \
bash /home/zhan/truffles-main/scripts/restart_release.sh"
```

After rollback:
1. Confirm script exits `0`
2. Confirm rollback guard artifact has `decision=go`
3. Confirm `/admin/health/check` still exposes `checks.knowledge_activation`

## Manual Guard Re-Run
If deploy already happened and only the canary artifact must be regenerated:
```bash
ssh -p 222 zhan@5.188.241.234 "python3 /home/zhan/truffles-main/truffles-api/scripts/knowledge_activation_release_guard.py \
--output /tmp/knowledge_activation_release_guard.manual.json \
--pretty"
```

## Decision Log Template
```text
activation_release_image:
timestamp_utc:
activation_service_restarted: yes|no
activation_guard_decision: go|no_go
activation_guard_reasons:
admin_activation_status:
metrics_missing:
operator:
decision: GO|NO_GO|ROLLBACK
notes:
```
