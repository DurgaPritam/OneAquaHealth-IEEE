"""Gemini vision provider (google-genai SDK, JSON schema output).

GEMINI_MODEL must be set explicitly: we do not hard-code a model id we have
not verified (see docs/OPEN_QUESTIONS.md OQ-10).
"""

from __future__ import annotations

import json
import os
import time

from api.ai.base import ProviderError, ProviderResult, Suggestion, build_prompt
from api.ai.labels import load_labels

SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["label", "confidence", "reason"],
}


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str | None = None) -> None:
        from google import genai

        self.model = model or os.environ.get("GEMINI_MODEL") or ""
        if not self.model:
            raise ProviderError("Set GEMINI_MODEL to use the Gemini provider")
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    def suggest(self, image: bytes, finding_type: str, allowed: list[str]) -> ProviderResult:
        from google.genai import types

        spec = load_labels()["types"][finding_type]["labels"]
        prompt = build_prompt(finding_type, allowed, {x["id"]: x["text"] for x in spec})
        start = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=[types.Part.from_bytes(data=image, mime_type="image/jpeg"), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=SCHEMA),
            )
            data = json.loads(response.text or "{}")
            suggestion = Suggestion(str(data["label"]), float(data["confidence"]), str(data["reason"]))
        except Exception as exc:  # the SDK raises several error types; all mean "answer manually"
            raise ProviderError(f"Gemini error: {exc.__class__.__name__}") from exc
        usage = getattr(response, "usage_metadata", None)
        return ProviderResult(
            [suggestion], self.name, self.model, (time.perf_counter() - start) * 1000,
            getattr(usage, "prompt_token_count", 0) or 0, getattr(usage, "candidates_token_count", 0) or 0,
        )
