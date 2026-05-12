#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "docs/GO_LIVE_DATA_READINESS.yaml"
DEFAULT_ENV_CANDIDATES = (
    ROOT / "truffles-api" / ".env",
    Path("/home/zhan/truffles-main/truffles-api/.env"),
)


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_repo_contract(repo_root: Path, config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for rule in (config.get("repo_contract") or {}).get("required_file_tokens") or []:
        rel_path = rule.get("path")
        tokens = rule.get("tokens") or []
        if not rel_path:
            continue
        path = repo_root / str(rel_path)
        if not path.exists():
            violations.append(f"required contract file missing -> {rel_path}")
            continue
        text = _read_text(path)
        for token in tokens:
            if token not in text:
                violations.append(f"{rel_path} missing required go-live data token -> {token}")
    return violations


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def resolve_env_file(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    for candidate in DEFAULT_ENV_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def apply_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    env = parse_env_file(path)
    for key, value in env.items():
        os.environ.setdefault(key, value)
    return env


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _required(config: dict[str, Any], key: str, default: Any = None) -> Any:
    checks = config.get("required_target_checks") or {}
    return checks.get(key, default)


def _report_only(config: dict[str, Any], key: str) -> bool:
    checks = config.get("report_only_checks") or {}
    return bool(checks.get(key, False))


def _minimum_data_summary(payload: Any, evaluator: Any, version: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "version": version,
            "ready": False,
            "missing_fields": ["client_pack"],
        }
    status = evaluator(payload)
    return {
        "version": version,
        "ready": bool(status.ready),
        "missing_fields": list(status.missing_fields),
    }


def _active_version(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    version = snapshot.get("active_version")
    return version if isinstance(version, dict) else None


def _target_errors(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    active_version = _active_version(target)
    minimum_data = active_version.get("minimum_data_contract") if isinstance(active_version, dict) else None
    errors: list[str] = []

    if not target.get("client_found"):
        errors.append("target client not found")
        return errors
    if not target.get("branch_found"):
        errors.append("target branch not found")
        return errors

    required_active = bool(_required(config, "branch_active", True))
    if bool(target.get("branch_active")) is not required_active:
        errors.append(
            f"target branch_active mismatch -> expected={required_active} actual={target.get('branch_active')}"
        )

    required_go_live = _required(config, "branch_go_live_state", "approved")
    if required_go_live and _normalize(target.get("go_live_state")) != _normalize(required_go_live):
        errors.append(
            f"target go_live_state mismatch -> expected={required_go_live} actual={target.get('go_live_state')}"
        )

    required_safe_mode = bool(_required(config, "knowledge_safe_mode", False))
    if bool(target.get("knowledge_safe_mode")) is not required_safe_mode:
        errors.append(
            f"target knowledge_safe_mode mismatch -> expected={required_safe_mode} actual={target.get('knowledge_safe_mode')}"
        )

    if active_version is None:
        errors.append("target active knowledge version missing")
    else:
        required_status = _required(config, "active_knowledge_status", "published")
        if required_status and _normalize(active_version.get("status")) != _normalize(required_status):
            errors.append(
                "target active knowledge status mismatch -> "
                f"expected={required_status} actual={active_version.get('status')}"
            )
        if not isinstance(minimum_data, dict):
            errors.append("target minimum data contract missing")
        else:
            required_version = _required(config, "minimum_data_contract_version")
            if required_version and minimum_data.get("version") != required_version:
                errors.append(
                    "target minimum data contract version mismatch -> "
                    f"expected={required_version} actual={minimum_data.get('version')}"
                )
            required_ready = bool(_required(config, "minimum_data_contract_ready", True))
            if bool(minimum_data.get("ready")) is not required_ready:
                errors.append(
                    "target minimum data readiness mismatch -> "
                    f"expected={required_ready} missing={minimum_data.get('missing_fields') or []}"
                )

    if bool(_required(config, "operational_service_integrity", False)):
        integrity = target.get("operational_data_integrity")
        if not isinstance(integrity, dict):
            errors.append("target operational service integrity missing")
        else:
            services_on_branch = int(integrity.get("services_on_branch") or 0)
            cross_client_links = int(integrity.get("cross_client_specialist_service_links") or 0)
            cross_branch_links = int(integrity.get("cross_branch_specialist_service_links") or 0)
            foreign_branch_services = int(integrity.get("service_rows_with_foreign_branch") or 0)
            if services_on_branch <= 0:
                errors.append("target branch service catalog empty")
            if cross_client_links > 0:
                errors.append(
                    "target specialist-service client mismatch -> "
                    f"count={cross_client_links}"
                )
            if cross_branch_links > 0:
                errors.append(
                    "target specialist-service branch mismatch -> "
                    f"count={cross_branch_links}"
                )
            if foreign_branch_services > 0:
                errors.append(
                    "target service rows point to foreign client branch -> "
                    f"count={foreign_branch_services}"
                )
    return errors


def _target_warnings(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    active_version = _active_version(target)
    warnings: list[str] = []
    if _report_only(config, "integration_state"):
        integration_state = _normalize(target.get("integration_state")) or "unknown"
        if integration_state != "ok":
            warnings.append(
                "target integration_state is report-only and not ok -> "
                f"state={target.get('integration_state')} reason={target.get('integration_reason')}"
            )
    if _report_only(config, "knowledge_sync_status") and active_version is not None:
        sync_status = _normalize(active_version.get("sync_status")) or "unknown"
        if sync_status != "ready":
            warnings.append(
                "target knowledge sync_status is report-only and not ready -> "
                f"version_id={active_version.get('id')} sync_status={active_version.get('sync_status')}"
            )
    return warnings


def _fleet_residuals(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    fleet = snapshot.get("fleet") if isinstance(snapshot.get("fleet"), dict) else {}
    branches = fleet.get("active_branches") if isinstance(fleet.get("active_branches"), list) else []
    residuals: list[dict[str, Any]] = []
    for item in branches:
        if not isinstance(item, dict):
            continue
        active_version = _active_version(item)
        if active_version is None:
            residuals.append(
                {
                    "client_slug": item.get("client_slug"),
                    "branch_slug": item.get("branch_slug"),
                    "branch_id": item.get("branch_id"),
                    "knowledge_tag": item.get("knowledge_tag"),
                    "missing_fields": ["knowledge_published"],
                    "reason": "active_knowledge_version_missing",
                }
            )
            continue
        minimum_data = active_version.get("minimum_data_contract")
        if isinstance(minimum_data, dict) and not bool(minimum_data.get("ready")):
            residuals.append(
                {
                    "client_slug": item.get("client_slug"),
                    "branch_slug": item.get("branch_slug"),
                    "branch_id": item.get("branch_id"),
                    "knowledge_tag": item.get("knowledge_tag"),
                    "active_version_id": active_version.get("id"),
                    "missing_fields": minimum_data.get("missing_fields") or [],
                    "reason": "active_payload_missing_minimum_data",
                }
            )
    return residuals


def _published_candidate_residuals(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    fleet = snapshot.get("fleet") if isinstance(snapshot.get("fleet"), dict) else {}
    branches = fleet.get("active_branches") if isinstance(fleet.get("active_branches"), list) else []
    residuals: list[dict[str, Any]] = []
    for item in branches:
        if not isinstance(item, dict):
            continue
        active_version = _active_version(item)
        if active_version is not None:
            continue
        candidate = item.get("latest_published_candidate")
        if not isinstance(candidate, dict):
            continue
        minimum_data = candidate.get("minimum_data_contract")
        if isinstance(minimum_data, dict) and not bool(minimum_data.get("ready")):
            residuals.append(
                {
                    "client_slug": item.get("client_slug"),
                    "branch_slug": item.get("branch_slug"),
                    "branch_id": item.get("branch_id"),
                    "candidate_version_id": candidate.get("id"),
                    "missing_fields": minimum_data.get("missing_fields") or [],
                    "reason": "published_candidate_missing_minimum_data",
                }
            )
    return residuals


def evaluate_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    repo_errors = list(snapshot.get("repo_contract_errors") or [])
    errors = repo_errors + _target_errors(snapshot, config)
    warnings = _target_warnings(snapshot, config)
    fleet_residuals = _fleet_residuals(snapshot)
    candidate_residuals = _published_candidate_residuals(snapshot)

    residual_policy = config.get("residual_policy") or {}
    if residual_policy.get("do_not_hide_fleet_missing_branches") and "fleet" not in snapshot:
        errors.append("fleet active branch residuals were not reported")

    if _report_only(config, "fleet_active_branch_residuals") and fleet_residuals:
        warnings.append(f"fleet active branch data residuals remain -> count={len(fleet_residuals)}")
    if _report_only(config, "published_candidate_residuals") and candidate_residuals:
        warnings.append(f"published candidate data residuals remain -> count={len(candidate_residuals)}")

    target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    active_version = _active_version(target)
    target_minimum = active_version.get("minimum_data_contract") if isinstance(active_version, dict) else {}

    return {
        "valid": not errors,
        "contract_name": config.get("contract_name"),
        "version": config.get("version"),
        "target": target,
        "target_verdict": {
            "data_ready": not _target_errors(snapshot, config),
            "minimum_data_contract_ready": bool(target_minimum.get("ready")) if isinstance(target_minimum, dict) else False,
            "operational_service_integrity_ready": not any(
                item.startswith("target branch service catalog")
                or item.startswith("target specialist-service")
                or item.startswith("target service rows")
                or item == "target operational service integrity missing"
                for item in _target_errors(snapshot, config)
            ),
            "integration_state_report_only": _report_only(config, "integration_state"),
            "knowledge_sync_status_report_only": _report_only(config, "knowledge_sync_status"),
        },
        "fleet_residuals": fleet_residuals,
        "published_candidate_residuals": candidate_residuals,
        "errors": errors,
        "warnings": warnings,
        "repo_contract_errors": repo_errors,
        "snapshot": snapshot,
    }


def _load_runtime_imports(repo_root: Path):
    api_root = repo_root / "truffles-api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
    import app.models  # noqa: F401
    from app.database import SessionLocal
    from app.models.branch import Branch
    from app.models.client import Client
    from app.models.knowledge_version import KnowledgeVersion
    from app.models.service import Service
    from app.models.specialist import Specialist
    from app.models.specialist_service import SpecialistService
    from app.services.knowledge_validation import MINIMUM_DATA_CONTRACT_VERSION, evaluate_minimum_data_contract

    return {
        "SessionLocal": SessionLocal,
        "Branch": Branch,
        "Client": Client,
        "KnowledgeVersion": KnowledgeVersion,
        "Service": Service,
        "Specialist": Specialist,
        "SpecialistService": SpecialistService,
        "MINIMUM_DATA_CONTRACT_VERSION": MINIMUM_DATA_CONTRACT_VERSION,
        "evaluate_minimum_data_contract": evaluate_minimum_data_contract,
    }


def _version_payload(version: Any, evaluator: Any, contract_version: str) -> dict[str, Any] | None:
    if version is None:
        return None
    payload_json = getattr(version, "payload_json", None)
    return {
        "id": str(getattr(version, "id", "")),
        "status": getattr(version, "status", None),
        "sync_status": getattr(version, "sync_status", None),
        "sync_error": getattr(version, "sync_error", None),
        "published_at": _jsonable(getattr(version, "published_at", None)),
        "created_at": _jsonable(getattr(version, "created_at", None)),
        "summary": getattr(version, "summary", None),
        "payload_type": "object" if isinstance(payload_json, dict) else type(payload_json).__name__,
        "minimum_data_contract": _minimum_data_summary(payload_json, evaluator, contract_version),
    }


def _latest_published(db: Any, KnowledgeVersion: Any, branch_id: Any) -> Any:
    return (
        db.query(KnowledgeVersion)
        .filter(KnowledgeVersion.branch_id == branch_id, KnowledgeVersion.status == "published")
        .order_by(KnowledgeVersion.published_at.desc().nullslast(), KnowledgeVersion.created_at.desc().nullslast())
        .first()
    )


def _active_version_for_branch(db: Any, KnowledgeVersion: Any, branch: Any) -> Any:
    active_version_id = getattr(branch, "active_knowledge_version_id", None)
    if not active_version_id:
        return None
    return db.query(KnowledgeVersion).filter(KnowledgeVersion.id == active_version_id).first()


def _operational_data_integrity(db: Any, imports: dict[str, Any], branch: Any, client: Any) -> dict[str, Any]:
    from sqlalchemy import func

    Branch = imports["Branch"]
    Service = imports["Service"]
    Specialist = imports["Specialist"]
    SpecialistService = imports["SpecialistService"]

    client_id = getattr(client, "id", None)
    branch_id = getattr(branch, "id", None)
    services_on_branch = (
        db.query(func.count(Service.id))
        .filter(Service.client_id == client_id, Service.branch_id == branch_id)
        .scalar()
        or 0
    )
    active_services_on_branch = (
        db.query(func.count(Service.id))
        .filter(Service.client_id == client_id, Service.branch_id == branch_id, Service.is_active.is_(True))
        .scalar()
        or 0
    )
    specialists_on_branch = (
        db.query(func.count(Specialist.id))
        .filter(Specialist.client_id == client_id, Specialist.branch_id == branch_id)
        .scalar()
        or 0
    )
    active_specialists_on_branch = (
        db.query(func.count(Specialist.id))
        .filter(Specialist.client_id == client_id, Specialist.branch_id == branch_id, Specialist.is_active.is_(True))
        .scalar()
        or 0
    )
    service_rows_with_foreign_branch = (
        db.query(func.count(Service.id))
        .join(Branch, Branch.id == Service.branch_id)
        .filter(Service.client_id == client_id, Branch.client_id != Service.client_id)
        .scalar()
        or 0
    )
    links = (
        db.query(SpecialistService, Specialist, Service)
        .join(Specialist, Specialist.id == SpecialistService.specialist_id)
        .join(Service, Service.id == SpecialistService.service_id)
        .filter(Specialist.client_id == client_id, Specialist.branch_id == branch_id)
        .all()
    )
    cross_client_examples: list[dict[str, Any]] = []
    cross_branch_examples: list[dict[str, Any]] = []
    for _, specialist, service in links:
        specialist_client_id = getattr(specialist, "client_id", None)
        specialist_branch_id = getattr(specialist, "branch_id", None)
        service_client_id = getattr(service, "client_id", None)
        service_branch_id = getattr(service, "branch_id", None)
        example = {
            "specialist_id": str(getattr(specialist, "id", "")),
            "specialist_name": getattr(specialist, "name", None),
            "specialist_branch_id": str(specialist_branch_id) if specialist_branch_id else None,
            "service_id": str(getattr(service, "id", "")),
            "service_name": getattr(service, "name", None),
            "service_branch_id": str(service_branch_id) if service_branch_id else None,
            "service_client_id": str(service_client_id) if service_client_id else None,
        }
        if service_client_id != specialist_client_id and len(cross_client_examples) < 10:
            cross_client_examples.append(example)
        if service_branch_id and service_branch_id != specialist_branch_id and len(cross_branch_examples) < 10:
            cross_branch_examples.append(example)

    return {
        "services_on_branch": int(services_on_branch),
        "active_services_on_branch": int(active_services_on_branch),
        "specialists_on_branch": int(specialists_on_branch),
        "active_specialists_on_branch": int(active_specialists_on_branch),
        "specialist_service_links": len(links),
        "cross_client_specialist_service_links": sum(
            1 for _, specialist, service in links if getattr(service, "client_id", None) != getattr(specialist, "client_id", None)
        ),
        "cross_branch_specialist_service_links": sum(
            1
            for _, specialist, service in links
            if getattr(service, "branch_id", None)
            and getattr(service, "branch_id", None) != getattr(specialist, "branch_id", None)
        ),
        "service_rows_with_foreign_branch": int(service_rows_with_foreign_branch),
        "cross_client_examples": cross_client_examples,
        "cross_branch_examples": cross_branch_examples,
    }


def _branch_snapshot(db: Any, imports: dict[str, Any], branch: Any, client: Any) -> dict[str, Any]:
    KnowledgeVersion = imports["KnowledgeVersion"]
    evaluator = imports["evaluate_minimum_data_contract"]
    contract_version = imports["MINIMUM_DATA_CONTRACT_VERSION"]
    active_version = _active_version_for_branch(db, KnowledgeVersion, branch)
    candidate = _latest_published(db, KnowledgeVersion, getattr(branch, "id", None))
    return {
        "client_id": str(getattr(client, "id", "")),
        "client_slug": getattr(client, "name", None),
        "client_status": getattr(client, "status", None),
        "client_config_business_type": (getattr(client, "config", None) or {}).get("business_type")
        if isinstance(getattr(client, "config", None), dict)
        else None,
        "branch_id": str(getattr(branch, "id", "")),
        "branch_slug": getattr(branch, "slug", None),
        "branch_name": getattr(branch, "name", None),
        "branch_active": bool(getattr(branch, "is_active", False)),
        "knowledge_tag": getattr(branch, "knowledge_tag", None),
        "go_live_state": getattr(branch, "go_live_state", None),
        "go_live_reason": getattr(branch, "go_live_reason", None),
        "go_live_reviewed_at": _jsonable(getattr(branch, "go_live_reviewed_at", None)),
        "integration_state": getattr(branch, "integration_state", None),
        "integration_reason": getattr(branch, "integration_reason", None),
        "integration_checked_at": _jsonable(getattr(branch, "integration_checked_at", None)),
        "knowledge_safe_mode": bool(getattr(branch, "knowledge_safe_mode", False)),
        "knowledge_safe_mode_reason": getattr(branch, "knowledge_safe_mode_reason", None),
        "active_knowledge_version_id": str(getattr(branch, "active_knowledge_version_id", ""))
        if getattr(branch, "active_knowledge_version_id", None)
        else None,
        "active_version": _version_payload(active_version, evaluator, contract_version),
        "latest_published_candidate": _version_payload(candidate, evaluator, contract_version),
        "operational_data_integrity": _operational_data_integrity(db, imports, branch, client),
    }


def collect_live_snapshot(repo_root: Path, config: dict[str, Any], *, env_file: Path | None) -> dict[str, Any]:
    loaded_env = apply_env_file(env_file)
    imports = _load_runtime_imports(repo_root)
    SessionLocal = imports["SessionLocal"]
    Client = imports["Client"]
    Branch = imports["Branch"]

    target_config = config.get("target") or {}
    client_slug = str(target_config.get("client_slug") or "").strip()
    branch_slug = str(target_config.get("branch_slug") or "").strip()

    with SessionLocal() as db:
        client = db.query(Client).filter(Client.name == client_slug).first() if client_slug else None
        branch = None
        if client is not None and branch_slug:
            branch = db.query(Branch).filter(Branch.client_id == client.id, Branch.slug == branch_slug).first()

        target: dict[str, Any]
        if client is None:
            target = {"client_slug": client_slug, "branch_slug": branch_slug, "client_found": False, "branch_found": False}
        elif branch is None:
            target = {
                "client_id": str(client.id),
                "client_slug": client.name,
                "branch_slug": branch_slug,
                "client_found": True,
                "branch_found": False,
            }
        else:
            target = _branch_snapshot(db, imports, branch, client)
            target["client_found"] = True
            target["branch_found"] = True

        active_branches = (
            db.query(Branch, Client)
            .join(Client, Client.id == Branch.client_id)
            .filter(Branch.is_active.is_(True))
            .order_by(Client.name.asc(), Branch.slug.asc())
            .all()
        )
        fleet = {
            "active_branches": [
                _branch_snapshot(db, imports, branch_item, client_item)
                for branch_item, client_item in active_branches
            ]
        }

    return {
        "env_file": str(env_file) if env_file else None,
        "env_file_loaded_keys": sorted(loaded_env.keys()),
        "minimum_data_contract_version": imports["MINIMUM_DATA_CONTRACT_VERSION"],
        "target": _jsonable(target),
        "fleet": _jsonable(fleet),
    }


def run_truth(repo_root: Path, config_path: Path, *, env_file: Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    repo_errors = validate_repo_contract(repo_root, config)
    snapshot = collect_live_snapshot(repo_root, config, env_file=env_file)
    snapshot["repo_contract_errors"] = repo_errors
    return evaluate_snapshot(snapshot, config)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the first go-live tenant data readiness truth.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    env_file = resolve_env_file(args.env_file)

    payload = run_truth(repo_root, config_path, env_file=env_file)
    rendered = json.dumps(_jsonable(payload), ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
