import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Agent, AgentIdentity, Branch, Client
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
    subject: str
    token_payload: dict[str, Any]


_jwks_client: Optional[PyJWKClient] = None


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


def _pick_agent_for_client(agents: list[Agent], client_id: UUID) -> Agent:
    role_priority = {"owner": 0, "admin": 1, "manager": 2, "support": 3}
    candidates = [agent for agent in agents if agent.client_id == client_id]
    if not candidates:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "No agent for selected client")
    return sorted(
        candidates,
        key=lambda agent: (
            role_priority.get(agent.role, 99),
            0 if agent.branch_id is None else 1,
            agent.name or "",
            str(agent.id),
        ),
    )[0]


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

    client_ids = {agent.client_id for agent in agents}
    clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
    clients_by_id = {client.id: client for client in clients}
    accessible_clients = sorted(clients_by_id.values(), key=lambda client: client.name)
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
        if selected_client_id not in clients_by_id:
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
    selected_agent = _pick_agent_for_client(agents, selected_client.id)

    branch_query = db.query(Branch).filter(Branch.client_id == selected_client.id)
    if selected_agent.branch_id:
        branch_query = branch_query.filter(Branch.id == selected_agent.branch_id)
    branches = branch_query.order_by(Branch.name.asc()).all()

    return ConsoleAuthContext(
        agent=selected_agent,
        client=selected_client,
        branches=branches,
        accessible_clients=accessible_clients,
        selection_required=selection_required,
        subject=str(subject),
        token_payload=payload,
    )
