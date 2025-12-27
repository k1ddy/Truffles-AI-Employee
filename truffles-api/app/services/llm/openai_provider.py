from typing import List, Optional

import httpx

from app.logging_config import get_logger
from app.services.llm.base import LLMProvider, LLMResponse

logger = get_logger("llm.openai")


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, default_model: str = "gpt-5-mini"):
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.audio_url = "https://api.openai.com/v1/audio/transcriptions"

    def generate(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout_seconds: Optional[float] = None,
    ) -> LLMResponse:
        """Generate response from OpenAI."""

        model = model or self.default_model

        timeout = timeout_seconds if timeout_seconds is not None else 60.0
        with httpx.Client(timeout=timeout) as client:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_tokens,
            }
            logger.debug(f"OpenAI request: model={model}, messages_count={len(messages)}")

            response = client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            logger.debug(f"OpenAI response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"OpenAI error: {response.text}")
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

            data = response.json()
            logger.debug(f"OpenAI full response: {data}")

            content = ""
            if data.get("choices") and len(data["choices"]) > 0:
                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                logger.debug(f"Choice: {choice}")
            logger.debug(f"OpenAI content: {content[:100] if content else 'EMPTY'}")

            return LLMResponse(
                content=content,
                model=data.get("model", model),
                usage=data.get("usage"),
            )

    def transcribe_audio(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> str:
        """Transcribe audio using OpenAI speech-to-text."""
        model = model or "whisper-1"
        if not audio_bytes:
            raise ValueError("audio_bytes is empty")

        files = {"file": (filename or "audio", audio_bytes, mime_type or "application/octet-stream")}
        data = {"model": model, "response_format": "text"}
        if prompt:
            data["prompt"] = prompt
        if language:
            data["language"] = language

        timeout = timeout_seconds if timeout_seconds is not None else 30.0
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                self.audio_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                files=files,
                data=data,
            )

        logger.debug(f"OpenAI transcription status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"OpenAI transcription error: {response.text}")
            raise Exception(f"OpenAI transcription error: {response.status_code} - {response.text}")

        transcript = (response.text or "").strip()
        if not transcript:
            logger.warning("OpenAI transcription returned empty text")
        return transcript
