from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.visit import Visit
from app.services.appointment_service import (
    AppointmentStatusValidationError,
    InvalidAppointmentTransitionError,
    SchedulingService,
)


def _query_with_first(result):
    query = Mock()
    query.filter.return_value.first.return_value = result
    return query


def _build_db(*, appointment, visit):
    db = Mock()
    appointment_query = _query_with_first(appointment)
    visit_query = _query_with_first(visit)

    def _query(model):
        if model is Appointment:
            return appointment_query
        if model is Visit:
            return visit_query
        raise AssertionError(f"Unexpected model query: {model}")

    db.query.side_effect = _query
    return db


def test_visit_transition_matrix_allows_expected_paths():
    assert SchedulingService.can_transition_to_visit_status("PENDING_CONFIRMATION", "COMPLETED")
    assert SchedulingService.can_transition_to_visit_status("CONFIRMED", "NO_SHOW")
    assert SchedulingService.can_transition_to_visit_status("RESCHEDULE_REQUESTED", "COMPLETED")
    assert SchedulingService.can_transition_to_visit_status("CHECKED_IN", "COMPLETED")
    assert SchedulingService.can_transition_to_visit_status("COMPLETED", "COMPLETED")
    assert not SchedulingService.can_transition_to_visit_status("CANCELLED", "COMPLETED")
    assert not SchedulingService.can_transition_to_visit_status("NO_SHOW", "COMPLETED")


def test_update_appointment_status_rejects_unknown_target_status():
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        specialist_id=uuid4(),
        user_id=None,
        status="CONFIRMED",
        version=1,
        notes=None,
        updated_at=None,
    )
    db = _build_db(appointment=appointment, visit=None)
    service = SchedulingService(db)

    with pytest.raises(AppointmentStatusValidationError):
        service.update_appointment_status(
            appointment_id=appointment.id,
            client_id=appointment.client_id,
            target_status="INVALID_STATUS",
            actor_id=uuid4(),
            commit=False,
        )


def test_update_appointment_status_rejects_invalid_transition():
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        specialist_id=uuid4(),
        user_id=None,
        status="CANCELLED",
        version=2,
        notes=None,
        updated_at=None,
    )
    db = _build_db(appointment=appointment, visit=None)
    service = SchedulingService(db)

    with pytest.raises(InvalidAppointmentTransitionError):
        service.update_appointment_status(
            appointment_id=appointment.id,
            client_id=appointment.client_id,
            target_status="COMPLETED",
            actor_id=uuid4(),
            commit=False,
        )


def test_update_appointment_status_creates_visit_and_audit():
    client_id = uuid4()
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=uuid4(),
        specialist_id=uuid4(),
        user_id=None,
        status="PENDING_CONFIRMATION",
        version=3,
        notes=None,
        updated_at=None,
    )
    db = _build_db(appointment=appointment, visit=None)
    service = SchedulingService(db)

    with patch("app.services.appointment_service.mark_pending_reminders_failed") as mark_failed:
        updated = service.update_appointment_status(
            appointment_id=appointment.id,
            client_id=client_id,
            target_status="COMPLETED",
            actor_id=uuid4(),
            reason="Пришел и обслужен",
            commit=False,
        )

    assert updated.status == "COMPLETED"
    assert updated.version == 4
    assert updated.updated_at is not None
    mark_failed.assert_called_once()

    added_rows = [call.args[0] for call in db.add.call_args_list]
    visit_rows = [row for row in added_rows if isinstance(row, Visit)]
    audit_rows = [row for row in added_rows if isinstance(row, AppointmentAudit)]
    assert len(visit_rows) == 1
    assert len(audit_rows) == 1
    assert visit_rows[0].status == "COMPLETED"
    assert visit_rows[0].arrived_at is not None
    assert visit_rows[0].completed_at is not None
    assert audit_rows[0].action == "status_update"
    assert audit_rows[0].new_status == "COMPLETED"


def test_update_appointment_status_idempotent_keeps_version_and_marks_audit():
    client_id = uuid4()
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=uuid4(),
        specialist_id=uuid4(),
        user_id=None,
        status="COMPLETED",
        version=5,
        notes=None,
        updated_at=datetime.now(timezone.utc),
    )
    existing_visit = SimpleNamespace(
        id=uuid4(),
        appointment_id=appointment.id,
        client_id=client_id,
        branch_id=appointment.branch_id,
        specialist_id=appointment.specialist_id,
        user_id=None,
        status="COMPLETED",
        arrived_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        visit_metadata={},
        created_by=None,
        created_at=datetime.now(timezone.utc),
    )
    db = _build_db(appointment=appointment, visit=existing_visit)
    service = SchedulingService(db)

    with patch("app.services.appointment_service.mark_pending_reminders_failed") as mark_failed:
        updated = service.update_appointment_status(
            appointment_id=appointment.id,
            client_id=client_id,
            target_status="COMPLETED",
            actor_id=uuid4(),
            commit=False,
        )

    assert updated.status == "COMPLETED"
    assert updated.version == 5
    mark_failed.assert_not_called()

    added_rows = [call.args[0] for call in db.add.call_args_list]
    visit_rows = [row for row in added_rows if isinstance(row, Visit)]
    audit_rows = [row for row in added_rows if isinstance(row, AppointmentAudit)]
    assert not visit_rows
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "status_update_idempotent"
