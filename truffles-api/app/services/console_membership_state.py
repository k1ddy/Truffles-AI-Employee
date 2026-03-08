from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Agent, AgentMembership, Branch, Client
from app.services.console_auth import ConsoleAuthContext
from app.services.console_errors import ConsoleAPIError

PRIVILEGED_ACCESS_ROLES = {"platform_admin", "owner", "admin"}
DEPRECATED_CONSOLE_ASSIGNMENT_ROLES = {"support", "specialist"}


def ensure_role_not_deprecated_for_assignment(role: Optional[str]) -> None:
    normalized_role = (role or "").strip().lower()
    if normalized_role in DEPRECATED_CONSOLE_ASSIGNMENT_ROLES:
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            f"{normalized_role} role is deprecated for assignment; use owner/admin/manager/viewer",
        )


def ensure_membership_role_is_assignable(role: Optional[str]) -> None:
    ensure_role_not_deprecated_for_assignment(role)
    if role == "platform_admin":
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "platform_admin role cannot be assigned via membership",
        )


def ensure_membership_agent_is_mutable(agent: Agent) -> None:
    if agent.role == "platform_admin":
        raise ConsoleAPIError(
            409,
            "INVALID_STATE",
            "platform_admin membership is managed automatically",
        )


def is_privileged_access_role(role: Optional[str]) -> bool:
    return (role or "").strip().lower() in PRIVILEGED_ACCESS_ROLES


def has_other_privileged_access_for_client(
    db: Session,
    *,
    client: Client,
    excluded_agent_ids: Optional[set[UUID]] = None,
    excluded_membership_ids: Optional[set[UUID]] = None,
) -> bool:
    excluded_agent_ids = excluded_agent_ids or set()
    excluded_membership_ids = excluded_membership_ids or set()

    platform_admin_query = db.query(Agent.id).filter(
        Agent.is_active.is_(True),
        Agent.role == "platform_admin",
    )
    if excluded_agent_ids:
        platform_admin_query = platform_admin_query.filter(~Agent.id.in_(excluded_agent_ids))
    if platform_admin_query.first():
        return True

    branch_ids = [row[0] for row in db.query(Branch.id).filter(Branch.client_id == client.id).all()]
    scope_filters = [and_(AgentMembership.scope == "client", AgentMembership.client_id == client.id)]
    if branch_ids:
        scope_filters.append(and_(AgentMembership.scope == "branch", AgentMembership.branch_id.in_(branch_ids)))
    if client.company_id:
        scope_filters.append(and_(AgentMembership.scope == "company", AgentMembership.company_id == client.company_id))

    membership_query = (
        db.query(AgentMembership.id)
        .join(Agent, Agent.id == AgentMembership.agent_id)
        .filter(
            Agent.is_active.is_(True),
            AgentMembership.is_active.is_(True),
            AgentMembership.role.in_(tuple(PRIVILEGED_ACCESS_ROLES)),
            or_(*scope_filters),
        )
    )
    if excluded_agent_ids:
        membership_query = membership_query.filter(~AgentMembership.agent_id.in_(excluded_agent_ids))
    if excluded_membership_ids:
        membership_query = membership_query.filter(~AgentMembership.id.in_(excluded_membership_ids))
    if membership_query.first():
        return True

    legacy_agent_query = db.query(Agent).filter(
        Agent.is_active.is_(True),
        Agent.client_id == client.id,
        Agent.role.in_(tuple(PRIVILEGED_ACCESS_ROLES)),
    )
    if excluded_agent_ids:
        legacy_agent_query = legacy_agent_query.filter(~Agent.id.in_(excluded_agent_ids))
    legacy_candidates = legacy_agent_query.all()
    if not legacy_candidates:
        return False

    candidate_ids = [agent.id for agent in legacy_candidates]
    membership_agent_ids = set()
    if candidate_ids:
        membership_agent_ids = {
            row[0]
            for row in db.query(AgentMembership.agent_id)
            .filter(AgentMembership.agent_id.in_(candidate_ids))
            .distinct()
            .all()
        }
    return any(agent.id not in membership_agent_ids for agent in legacy_candidates)


def ensure_membership_change_keeps_privileged_access(
    db: Session,
    *,
    context: ConsoleAuthContext,
    membership: AgentMembership,
    agent: Agent,
    next_role: str,
    next_is_active: bool,
) -> None:
    current_privileged = membership.is_active and is_privileged_access_role(membership.role)
    next_privileged = next_is_active and is_privileged_access_role(next_role)
    if not current_privileged or next_privileged:
        return
    if membership.agent_id == context.agent.id:
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable or downgrade your own privileged membership")

    client = db.query(Client).filter(Client.id == agent.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    if not has_other_privileged_access_for_client(
        db,
        client=client,
        excluded_membership_ids={membership.id},
    ):
        raise ConsoleAPIError(
            409,
            "INVALID_STATE",
            "Cannot remove last active privileged membership for this client",
        )


def ensure_agent_lifecycle_is_mutable(
    db: Session,
    *,
    context: ConsoleAuthContext,
    agent: Agent,
    enabling: bool,
) -> None:
    if agent.role == "platform_admin":
        raise ConsoleAPIError(409, "INVALID_STATE", "platform_admin account is protected")
    if not enabling and agent.id == context.agent.id:
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable your own account")
    if enabling or not is_privileged_access_role(agent.role):
        return

    client = db.query(Client).filter(Client.id == agent.client_id).first()
    if not client:
        raise ConsoleAPIError(404, "NOT_FOUND", "Client not found")
    if not has_other_privileged_access_for_client(
        db,
        client=client,
        excluded_agent_ids={agent.id},
    ):
        raise ConsoleAPIError(409, "INVALID_STATE", "Cannot disable the last active privileged account for this client")
