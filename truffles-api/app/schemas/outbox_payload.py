from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator


def _summarize_validation_error(exc: ValidationError, *, limit: int = 3) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = item.get("loc") or []
        loc_text = ".".join(str(entry) for entry in loc) if loc else ""
        msg = item.get("msg") or "invalid"
        if loc_text:
            parts.append(f"{loc_text}:{msg}")
        else:
            parts.append(msg)
        if len(parts) >= limit:
            break
    return "; ".join(parts) or "invalid_payload"


class OutboxPayloadMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sender: str | None = None
    timestamp: int | None = None
    messageId: str | None = None
    remoteJid: str = Field(..., min_length=1)
    simulation_mode: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("simulation_mode", "simulationMode"),
    )
    simulation_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("simulation_id", "simulationId"),
    )
    simulation_llm: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("simulation_llm", "simulationLlm"),
    )
    instanceId: str | None = Field(
        default=None,
        validation_alias=AliasChoices("instanceId", "instance_id", "instance"),
    )
    forwarded_to_telegram: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("forwarded_to_telegram", "forwardedToTelegram"),
    )


class OutboxPayloadBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messageType: str = "text"
    message: str | None = None
    metadata: OutboxPayloadMetadata
    mediaData: Any | None = None

    @model_validator(mode="after")
    def _ensure_content(self) -> "OutboxPayloadBody":
        message = (self.message or "").strip()
        message_type = (self.messageType or "").strip().lower()
        has_media = bool(self.mediaData) or (message_type and message_type != "text")
        if not message and not has_media:
            raise ValueError("message_or_media_required")
        return self


class OutboxPayloadContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: OutboxPayloadBody
    client_slug: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _normalize_client_slug(self) -> "OutboxPayloadContract":
        if not self.client_slug or not self.client_slug.strip():
            raise ValueError("client_slug_required")
        self.client_slug = self.client_slug.strip()
        return self


def validate_outbox_payload(
    payload_json: dict[str, Any],
    *,
    expected_client_slug: str | None = None,
) -> tuple[OutboxPayloadContract | None, str | None]:
    try:
        contract = OutboxPayloadContract.model_validate(payload_json)
    except ValidationError as exc:
        return None, f"contract_error:{_summarize_validation_error(exc)}"

    if expected_client_slug and contract.client_slug != expected_client_slug:
        return None, "client_slug_mismatch"

    return contract, None
