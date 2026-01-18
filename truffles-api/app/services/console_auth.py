import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Optional

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


def get_console_context(request: Request, db: Session) -> ConsoleAuthContext:
    token = _get_bearer_token(request)
    payload = _decode_token(token)
    subject = payload.get("sub")
    if not subject:
        raise ConsoleAPIError(401, "TOKEN_INVALID", "Missing subject claim")

    identity = (
        db.query(AgentIdentity)
        .filter(AgentIdentity.channel == "oidc", AgentIdentity.external_id == subject)
        .first()
    )
    if not identity or not identity.agent:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "No console access for this identity")
    agent = identity.agent
    if not agent.is_active:
        raise ConsoleAPIError(403, "ACCOUNT_DISABLED", "Agent is disabled")

    client = db.query(Client).filter(Client.id == agent.client_id).first()
    if not client:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Client not found for agent")

    branch_query = db.query(Branch).filter(Branch.client_id == client.id)
    if agent.branch_id:
        branch_query = branch_query.filter(Branch.id == agent.branch_id)
    branches = branch_query.order_by(Branch.name.asc()).all()

    return ConsoleAuthContext(
        agent=agent,
        client=client,
        branches=branches,
        subject=str(subject),
        token_payload=payload,
    )
