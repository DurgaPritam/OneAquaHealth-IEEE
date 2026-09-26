"""Claude vision provider (official Anthropic SDK, structured output)."""

from __future__ import annotations

import base64
import os
import time

from pydantic import BaseModel, Field

from api.ai.base import ProviderError, ProviderResult, Suggestion, build_prompt
from api.ai.labels import load_labels

DEFAULT_MODEL = "claude-opus-5"


class _Answer(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        import anthropic  # imported lazily so the mock path needs no SDK

        self.model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self._client = anthropic.Anthropic()
        self._sdk = anthropic

    def suggest(self, image: bytes, finding_type: str, allowed: list[str]) -> ProviderResult:
        spec = load_labels()["types"][finding_type]["labels"]
        prompt = build_prompt(finding_type, allowed, {x["id"]: x["text"] for x in spec})
        start = time.perf_counter()
        try:
            response = self._client.beta.messages.parse(
                model=self.model,
                max_tokens=1024,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low"},
                output_format=_Answer,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(image).decode()}},
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
        except self._sdk.APIError as exc:
            raise ProviderError(f"Anthropic API error: {exc.__class__.__name__}") from exc
        latency = (time.perf_counter() - start) * 1000
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise ProviderError("The model declined or returned no structured answer")
        answer = response.parsed_output
        return ProviderResult(
            [Suggestion(answer.label, answer.confidence, answer.reason)],
            self.name, self.model, latency,
            response.usage.input_tokens, response.usage.output_tokens,
        )
