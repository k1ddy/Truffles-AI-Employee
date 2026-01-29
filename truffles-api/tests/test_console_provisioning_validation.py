from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.console import ConsoleClientCreateRequest


def test_console_client_create_requires_company_id():
    with pytest.raises(ValidationError):
        ConsoleClientCreateRequest(slug="demo_salon")


def test_console_client_create_accepts_company_id():
    payload = ConsoleClientCreateRequest(slug="demo_salon", company_id=uuid4())
    assert payload.company_id is not None
