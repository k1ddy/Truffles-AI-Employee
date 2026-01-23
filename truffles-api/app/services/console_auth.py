import base64
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Agent, AgentIdentity, AgentMembership, Branch, Client
from app.services.console_errors import ConsoleAPIError

try:
    from jwt import InvalidTokenError, PyJWKClient
    from jwt import decode as jwt_decode
except Exception:  # pragma: no cover - optional dependency for dev scaffold
    InvalidTokenError = Exception
    PyJWKClient = None
    jwt_decode = None


@dataclass
class ConsoleAuthContext:
    agent: Agent
    client: Client
    branches: list[Branch]
    accessible_clients: list[Client]
    selection_required: bool
    role: str
    allowed_branch_ids: set[UUID]
    branch_restricted: bool
    effective_branch_id: Optional[UUID]
    branch_selection_required: bool
    selected_branch_id: Optional[UUID]
    subject: str
    token_payload: dict[str, Any]


_jwks_client: Optional[PyJWKClient] = None
_role_priority = {"owner": 0, "admin": 1, "manager": 2, "support": 3}


@dataclass
class _AccessEntry:
    roles: set[str] = field(default_factory=set)
    scopes: set[str] = field(default_factory=set)
    branch_ids: set[UUID] = field(default_factory=set)
    agent_ids: set[UUID] = field(default_factory=set)


def _get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise ConsoleAPIError(401, "AUTH_REQUIRED", "Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ConsoleAPIError(401, "AUTH_REQUIRED", "Missing bearer token")
    return token


def _decode_unverified_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Invalid JWT format")
    payload_b64 = parts[1] + "==="
    try:
        payload_raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        return json.loads(payload_raw.decode("utf-8"))
    except Exception as exc:
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Failed to decode JWT payload") from exc


def _verify_expected_claims(payload: dict[str, Any]) -> None:
    issuer = os.environ.get("CONSOLE_OIDC_ISSUER")
    audience = os.environ.get("CONSOLE_OIDC_AUDIENCE")
    if issuer and payload.get("iss") != issuer:
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Issuer mismatch")
    if audience:
        aud = payload.get("aud")
        if isinstance(aud, str):
            valid = aud == audience
        elif isinstance(aud, list):
            valid = audience in aud
        else:
            valid = False
        if not valid:
            raise ConsoleAPIError(401, "TOKEN_INVALID", "Audience mismatch")


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None or getattr(_jwks_client, "jwks_uri", None) != jwks_url:
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def _decode_verified_payload(token: str) -> dict[str, Any]:
    if jwt_decode is None or PyJWKClient is None:
        raise ConsoleAPIError(500, "OIDC_DEPENDENCY_MISSING", "PyJWT is required for OIDC validation")
    jwks_url = os.environ.get("CONSOLE_OIDC_JWKS_URL")
    if not jwks_url:
        raise ConsoleAPIError(500, "OIDC_NOT_CONFIGURED", "CONSOLE_OIDC_JWKS_URL is not set")
    issuer = os.environ.get("CONSOLE_OIDC_ISSUER")
    audience = os.environ.get("CONSOLE_OIDC_AUDIENCE")
    algorithms_env = os.environ.get("CONSOLE_OIDC_ALGORITHMS", "RS256")
    algorithms = [value.strip() for value in algorithms_env.split(",") if value.strip()]
    jwk_client = _get_jwks_client(jwks_url)
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        return jwt_decode(
            token,
            signing_key.key,
            algorithms=algorithms,
            audience=audience,
            issuer=issuer,
            options={"verify_aud": bool(audience), "verify_iss": bool(issuer)},
        )
    except InvalidTokenError as exc:
        print(f"DEBUG: JWT Validation Error: {exc}")
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Token validation failed") from exc


def _decode_token(token: str) -> dict[str, Any]:
    print(f"DEBUG: Decoding token. JWKS_URL={os.environ.get('CONSOLE_OIDC_JWKS_URL')}, ALLOW_UNVERIFIED={os.environ.get('CONSOLE_OIDC_ALLOW_UNVERIFIED')}")
    if os.environ.get("CONSOLE_OIDC_JWKS_URL"):
        return _decode_verified_payload(token)
    if os.environ.get("CONSOLE_OIDC_ALLOW_UNVERIFIED", "0") == "1":
        try:
            payload = _decode_unverified_payload(token)
            print(f"DEBUG: Unverified payload: {payload}")
            _verify_expected_claims(payload)
            return payload
        except Exception as e:
            print(f"DEBUG: Error in unverified decoding: {e}")
            raise
    raise ConsoleAPIError(
        500,
        "OIDC_NOT_CONFIGURED",
        "OIDC validation is not configured (set CONSOLE_OIDC_JWKS_URL)",
    )


def _parse_client_header(request: Request) -> Optional[UUID]:
    raw_client_id = request.headers.get("x-client-id")
    if not raw_client_id:
        return None
    try:
        return UUID(raw_client_id)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid X-Client-Id header") from exc


def _parse_branch_header(request: Request) -> Optional[UUID]:
    raw_branch_id = request.headers.get("x-branch-id")
    if not raw_branch_id:
        return None
    try:
        return UUID(raw_branch_id)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid X-Branch-Id header") from exc


def _resolve_branch_selection(
    allowed_branch_ids: set[UUID],
    *,
    branch_restricted: bool,
    selected_branch_id: Optional[UUID],
    require_selection: bool,
) -> tuple[Optional[UUID], bool]:
    branch_selection_required = False
    effective_branch_id = None
    if selected_branch_id:
        if selected_branch_id not in allowed_branch_ids:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
        effective_branch_id = selected_branch_id
    elif branch_restricted and len(allowed_branch_ids) == 1:
        effective_branch_id = next(iter(allowed_branch_ids))
    elif branch_restricted and len(allowed_branch_ids) > 1:
        branch_selection_required = True
        if require_selection:
            raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Branch selection required")
    return effective_branch_id, branch_selection_required


def _pick_agent_for_client(agents: list[Agent], client_id: UUID) -> Agent:
    candidates = [agent for agent in agents if agent.client_id == client_id]
    if not candidates:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "No agent for selected client")
    return sorted(
        candidates,
        key=lambda agent: (
            _role_priority.get(agent.role, 99),
            0 if agent.branch_id is None else 1,
            agent.name or "",
            str(agent.id),
        ),
    )[0]


def _pick_agent_for_access(agents: list[Agent]) -> Agent:
    if not agents:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "No agent available for access")
    return sorted(
        agents,
        key=lambda agent: (
            _role_priority.get(agent.role, 99),
            0 if agent.branch_id is None else 1,
            agent.name or "",
            str(agent.id),
        ),
    )[0]


def _resolve_role(roles: set[str]) -> Optional[str]:
    if not roles:
        return None
    return sorted(roles, key=lambda role: _role_priority.get(role, 99))[0]


def _add_access_entry(
    access_map: dict[UUID, _AccessEntry],
    client_id: UUID,
    role: str,
    scope: str,
    branch_id: Optional[UUID],
    agent_id: UUID,
) -> None:
    entry = access_map.setdefault(client_id, _AccessEntry())
    entry.roles.add(role)
    entry.scopes.add(scope)
    if branch_id:
        entry.branch_ids.add(branch_id)
    entry.agent_ids.add(agent_id)


def _build_access_map(
    memberships: list[AgentMembership],
    legacy_agents: list[Agent],
    branches_by_id: dict[UUID, Branch],
    clients_by_company: dict[UUID, list[Client]],
    clients_by_id: dict[UUID, Client],
) -> dict[UUID, _AccessEntry]:
    access_map: dict[UUID, _AccessEntry] = {}

    for membership in memberships:
        if membership.scope == "company":
            for client in clients_by_company.get(membership.company_id, []):
                _add_access_entry(access_map, client.id, membership.role, "company", None, membership.agent_id)
        elif membership.scope == "client":
            if membership.client_id in clients_by_id:
                _add_access_entry(access_map, membership.client_id, membership.role, "client", None, membership.agent_id)
        elif membership.scope == "branch":
            branch = branches_by_id.get(membership.branch_id)
            if branch:
                _add_access_entry(access_map, branch.client_id, membership.role, "branch", branch.id, membership.agent_id)

    for agent in legacy_agents:
        if agent.branch_id:
            _add_access_entry(access_map, agent.client_id, agent.role, "branch", agent.branch_id, agent.id)
        else:
            _add_access_entry(access_map, agent.client_id, agent.role, "client", None, agent.id)

    return access_map


def get_console_context(request: Request, db: Session, *, require_selection: bool = True) -> ConsoleAuthContext:
    token = _get_bearer_token(request)
    payload = _decode_token(token)
    subject = payload.get("sub")
    if not subject:
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Missing subject claim")

    identities = (
        db.query(AgentIdentity)
        .join(Agent)
        .filter(AgentIdentity.channel == "oidc", AgentIdentity.external_id == subject)
        .all()
    )
    if not identities:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "No console access for this identity")

    agents_by_id: dict[UUID, Agent] = {}
    for identity in identities:
        agent = identity.agent
        if agent and agent.is_active:
            agents_by_id[agent.id] = agent
    agents = list(agents_by_id.values())
    if not agents:
        raise ConsoleAPIError(403, "ACCOUNT_DISABLED", "Agent is disabled")

    agent_ids = list(agents_by_id.keys())
    memberships = []
    if agent_ids:
        memberships = (
            db.query(AgentMembership)
            .filter(AgentMembership.agent_id.in_(agent_ids), AgentMembership.is_active == True)
            .all()
        )

    memberships_by_agent: dict[UUID, list[AgentMembership]] = defaultdict(list)
    for membership in memberships:
        memberships_by_agent[membership.agent_id].append(membership)

    legacy_agents = [agent for agent in agents if not memberships_by_agent.get(agent.id)]

    membership_branch_ids = {m.branch_id for m in memberships if m.scope == "branch" and m.branch_id}
    membership_client_ids = {m.client_id for m in memberships if m.scope == "client" and m.client_id}
    membership_company_ids = {m.company_id for m in memberships if m.scope == "company" and m.company_id}

    legacy_branch_ids = {agent.branch_id for agent in legacy_agents if agent.branch_id}
    legacy_client_ids = {agent.client_id for agent in legacy_agents if agent.client_id}

    branch_ids = membership_branch_ids | legacy_branch_ids
    branches_by_id: dict[UUID, Branch] = {}
    if branch_ids:
        branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
        branches_by_id = {branch.id: branch for branch in branches}

    branch_client_ids = {branch.client_id for branch in branches_by_id.values()}

    company_clients = []
    if membership_company_ids:
        company_clients = db.query(Client).filter(Client.company_id.in_(membership_company_ids)).all()

    clients_by_company: dict[UUID, list[Client]] = defaultdict(list)
    for client in company_clients:
        if client.company_id:
            clients_by_company[client.company_id].append(client)

    client_ids = set(membership_client_ids) | legacy_client_ids | branch_client_ids | {client.id for client in company_clients}
    clients_by_id: dict[UUID, Client] = {}
    if client_ids:
        clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
        clients_by_id = {client.id: client for client in clients}

    access_map = _build_access_map(
        memberships=memberships,
        legacy_agents=legacy_agents,
        branches_by_id=branches_by_id,
        clients_by_company=clients_by_company,
        clients_by_id=clients_by_id,
    )

    accessible_clients = sorted(
        [clients_by_id[client_id] for client_id in access_map.keys() if client_id in clients_by_id],
        key=lambda client: client.name,
    )
    if not accessible_clients:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Client not found for agent")

    try:
        selected_client_id = _parse_client_header(request)
    except ConsoleAPIError:
        if require_selection:
            raise
        selected_client_id = None
    selection_required = False
    if selected_client_id:
        if selected_client_id not in access_map:
            if require_selection:
                raise ConsoleAPIError(403, "TENANT_MISMATCH", "Client access denied")
            selected_client_id = None
    elif len(accessible_clients) == 1:
        selected_client_id = accessible_clients[0].id
    else:
        selection_required = True
        if require_selection:
            raise ConsoleAPIError(400, "CLIENT_SELECTION_REQUIRED", "Client selection required")

    selected_client = clients_by_id.get(selected_client_id) if selected_client_id else accessible_clients[0]
    access_entry = access_map.get(selected_client.id, _AccessEntry())

    candidate_agents = [
        agents_by_id[agent_id] for agent_id in access_entry.agent_ids if agent_id in agents_by_id
    ]
    preferred_agents = [agent for agent in candidate_agents if agent.client_id == selected_client.id]
    selected_agent = _pick_agent_for_access(preferred_agents or candidate_agents or agents)

    effective_role = _resolve_role(access_entry.roles) or selected_agent.role

    branches_for_client = (
        db.query(Branch)
        .filter(Branch.client_id == selected_client.id)
        .order_by(Branch.name.asc())
        .all()
    )

    branch_restricted = "client" not in access_entry.scopes and "company" not in access_entry.scopes
    if branch_restricted:
        allowed_branch_ids = set(access_entry.branch_ids)
        branches = [branch for branch in branches_for_client if branch.id in allowed_branch_ids]
    else:
        allowed_branch_ids = {branch.id for branch in branches_for_client}
        branches = branches_for_client

    selected_branch_id: Optional[UUID] = None
    try:
        selected_branch_id = _parse_branch_header(request)
    except ConsoleAPIError:
        if require_selection:
            raise
        selected_branch_id = None

    effective_branch_id, branch_selection_required = _resolve_branch_selection(
        allowed_branch_ids,
        branch_restricted=branch_restricted,
        selected_branch_id=selected_branch_id,
        require_selection=require_selection,
    )

    return ConsoleAuthContext(
        agent=selected_agent,
        client=selected_client,
        branches=branches,
        accessible_clients=accessible_clients,
        selection_required=selection_required,
        role=effective_role,
        allowed_branch_ids=allowed_branch_ids,
        branch_restricted=branch_restricted,
        effective_branch_id=effective_branch_id,
        branch_selection_required=branch_selection_required,
        selected_branch_id=selected_branch_id,
        subject=str(subject),
        token_payload=payload,
    )
