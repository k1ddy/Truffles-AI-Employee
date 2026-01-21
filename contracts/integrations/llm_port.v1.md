# LLM Port v1

Purpose
- Standardize LLM usage (chat, embeddings, moderation) behind a single port.
- Allow vendor swap (OpenAI-compatible, LiteLLM gateway, vLLM).

Interface
- chat_completion(request: ChatCompletionRequest) -> Result[ChatCompletionResult]
- embeddings(request: EmbeddingsRequest) -> Result[EmbeddingsResult]
- moderation(request: ModerationRequest) -> Result[ModerationResult]

ChatCompletionRequest
- model: string
- messages: list[{role: "system"|"user"|"assistant", content: string}]
- temperature: number | null
- max_tokens: integer | null
- metadata: object (trace_id, client_id, policy hints)

ChatCompletionResult
- content: string
- finish_reason: string | null
- usage: {prompt_tokens: int, completion_tokens: int, total_tokens: int}
- raw: object

EmbeddingsRequest
- model: string
- input: string | list[string]
- metadata: object

EmbeddingsResult
- vectors: list[list[number]]
- usage: {prompt_tokens: int, total_tokens: int}
- raw: object

ModerationRequest
- model: string
- input: string
- metadata: object

ModerationResult
- flagged: boolean
- categories: object
- raw: object

Rules
- Errors are returned as Result.fail with a stable code (e.g. LLM_TIMEOUT, LLM_RATE_LIMIT).
- Port must not invent facts; it only returns model outputs and metadata.
- Timeouts are enforced in adapter, not in core.

Notes
- Breaking changes require a new version file (llm_port.v2.md).
