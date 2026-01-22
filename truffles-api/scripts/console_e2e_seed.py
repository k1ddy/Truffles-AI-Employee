import json
import os
import sys
import uuid
from datetime import datetime, timezone
from urllib import parse, request
from urllib.error import HTTPError, URLError

SCRIPT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(SCRIPT_ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Agent, AgentIdentity, Branch, Client, Company, Conversation, Handover, User

NAMESPACE = uuid.UUID("c7b4195c-2b92-4dfd-8a40-5b7a8e2f8f0b")


def stable_uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name}")
    return value


def fetch_keycloak_subject(
    base_url: str,
    realm: str,
    username: str,
    admin_username: str,
    admin_password: str,
) -> str:
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
    payload = parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin_username,
            "password": admin_password,
        }
    ).encode("utf-8")
    token_req = request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with request.urlopen(token_req) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Keycloak admin token failed: {exc}") from exc

    access_token = token_payload.get("access_token")
    if not access_token:
        raise SystemExit("Keycloak admin token missing access_token")

    users_url = f"{base_url}/admin/realms/{realm}/users"
    users_url = f"{users_url}?username={parse.quote(username)}&exact=true"
    users_req = request.Request(users_url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with request.urlopen(users_req) as response:
            users = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Keycloak user lookup failed: {exc}") from exc

    if not users:
        raise SystemExit(f"Keycloak user not found: {username}")
    return users[0]["id"]


def get_or_create(session: Session, model, obj_id, **fields):
    instance = session.get(model, obj_id)
    if instance:
        return instance, False
    instance = model(id=obj_id, **fields)
    session.add(instance)
    return instance, True


def main() -> None:
    if os.environ.get("E2E_SEED_ALLOW") != "1":
        raise SystemExit("E2E_SEED_ALLOW=1 is required")

    e2e_username = os.environ.get("E2E_USERNAME") or os.environ.get("CONSOLE_E2E_USERNAME")
    if not e2e_username:
        raise SystemExit("Missing E2E_USERNAME or CONSOLE_E2E_USERNAME")

    subject = os.environ.get("E2E_SUBJECT", "").strip()
    if not subject:
        issuer = os.environ.get("KEYCLOAK_ISSUER", "").strip()
        base_url = os.environ.get("KEYCLOAK_ADMIN_BASE_URL", "").strip()
        realm = os.environ.get("KEYCLOAK_REALM", "").strip()
        if not base_url:
            if issuer and "/realms/" in issuer:
                base_url = issuer.split("/realms/")[0]
        if not base_url:
            raise SystemExit("Missing KEYCLOAK_ADMIN_BASE_URL or KEYCLOAK_ISSUER")
        if not realm and issuer and "/realms/" in issuer:
            realm = issuer.split("/realms/")[1]
        if not realm:
            raise SystemExit("Missing KEYCLOAK_REALM")
        admin_username = require_env("KEYCLOAK_ADMIN_USERNAME")
        admin_password = require_env("KEYCLOAK_ADMIN_PASSWORD")
        subject = fetch_keycloak_subject(base_url, realm, e2e_username, admin_username, admin_password)

    now = datetime.now(timezone.utc)
    engine = create_engine(settings.database_url)
    session = Session(engine)

    company_id = stable_uuid("console-e2e:company")
    client_id = stable_uuid("console-e2e:client")
    branch_id = stable_uuid("console-e2e:branch")
    agent_id = stable_uuid("console-e2e:agent")
    identity_id = stable_uuid("console-e2e:identity")
    user_id = stable_uuid("console-e2e:user")
    conversation_id = stable_uuid("console-e2e:conversation")
    handover_id = stable_uuid("console-e2e:handover")

    company, _ = get_or_create(
        session,
        Company,
        company_id,
        name="Console E2E",
        billing_info={},
        created_at=now,
        updated_at=now,
    )

    client, _ = get_or_create(
        session,
        Client,
        client_id,
        name="Console E2E",
        status="active",
        config={},
        created_at=now,
        updated_at=now,
        company_id=company.id,
    )

    branch, _ = get_or_create(
        session,
        Branch,
        branch_id,
        client_id=client.id,
        slug="console-e2e-main",
        name="Console E2E Main",
        instance_id="console-e2e",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    agent, _ = get_or_create(
        session,
        Agent,
        agent_id,
        client_id=client.id,
        branch_id=branch.id,
        role="owner",
        name=e2e_username,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    identity = (
        session.query(AgentIdentity)
        .filter(
            AgentIdentity.channel == "oidc",
            AgentIdentity.external_id == subject,
            AgentIdentity.agent_id == agent.id,
        )
        .first()
    )
    if not identity:
        identity = AgentIdentity(
            id=identity_id,
            agent_id=agent.id,
            channel="oidc",
            external_id=subject,
            username=e2e_username,
            created_at=now,
            updated_at=now,
        )
        session.add(identity)

    user, _ = get_or_create(
        session,
        User,
        user_id,
        client_id=client.id,
        name="E2E Customer",
        created_at=now,
        user_metadata={},
    )

    conversation, _ = get_or_create(
        session,
        Conversation,
        conversation_id,
        client_id=client.id,
        branch_id=branch.id,
        user_id=user.id,
        channel="telegram",
        status="handover",
        started_at=now,
        last_message_at=now,
        context={},
    )

    handover, _ = get_or_create(
        session,
        Handover,
        handover_id,
        conversation_id=conversation.id,
        client_id=client.id,
        trigger_type="manual",
        status="pending",
        created_at=now,
        user_message="E2E seeded case",
        channel="telegram",
    )

    session.commit()
    session.close()

    print("E2E seed complete:")
    print(f"- company_id={company.id}")
    print(f"- client_id={client.id}")
    print(f"- branch_id={branch.id}")
    print(f"- agent_id={agent.id}")
    print(f"- identity_external_id={subject}")
    print(f"- conversation_id={conversation.id}")
    print(f"- handover_id={handover.id}")


if __name__ == "__main__":
    main()
