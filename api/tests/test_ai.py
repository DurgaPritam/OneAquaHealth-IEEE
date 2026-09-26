from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.ai import gbif, service
from api.ai.base import ProviderError, ProviderResult, Suggestion
from api.ai.gate import apply_gate
from api.ai.keys import compare, run_key
from api.ai.labels import allowed, load_labels
from api.ai.mock import MockProvider


class FixedProvider:
    """Returns whatever suggestions the test gives it."""

    name = "fixed"
    model = "fixed-1"

    def __init__(self, suggestions: list[Suggestion]) -> None:
        self.suggestions = suggestions
        self.calls = 0

    def suggest(self, image: bytes, finding_type: str, allowed_: list[str]) -> ProviderResult:
        self.calls += 1
        return ProviderResult(self.suggestions, self.name, self.model, 1.0)


class FailingProvider:
    name = "failing"
    model = "x"

    def suggest(self, *_: object) -> ProviderResult:
        raise ProviderError("down")


def jpeg(colour=(10, 120, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(buf, format="JPEG")
    return buf.getvalue()


# ------------------------------------------------------------ labels and gate


def test_labels_file_has_no_species_for_larvae_or_dead_birds() -> None:
    types = load_labels()["types"]
    assert types["dead_bird"]["labels"] == []
    for label in allowed("larvae") + allowed("adult_mosquito"):
        assert " " not in label, "larva and adult labels are types, not binomial species names"


@pytest.mark.parametrize("invented", ["Culex pipiens", "west_nile_positive", "infected", "Aedes albopictus (confirmed)", "", "LARVAE_PRESENT"])
def test_gate_drops_invented_labels(invented: str) -> None:
    result = apply_gate("larvae", [Suggestion(invented, 0.99, "Clearly visible"), Suggestion("larvae_present", 0.7, "Wrigglers in the cup")])
    assert [s.label for s in result.kept] == ["larvae_present"]
    assert result.dropped == [{"label": invented, "why": "not in the allowed label list"}]


def test_gate_drops_bad_confidence_and_missing_reason() -> None:
    result = apply_gate("habitat", [Suggestion("standing_water", 1.4, "x"), Suggestion("flowing_water", 0.5, "  ")])
    assert result.kept == []
    assert {d["why"] for d in result.dropped} == {"confidence outside 0 to 1", "no reason given"}


def test_gate_uses_per_type_lists() -> None:
    # a valid predator label is still invented for larvae
    result = apply_gate("larvae", [Suggestion("Bufo bufo", 0.8, "Toad")])
    assert result.kept == [] and result.dropped[0]["label"] == "Bufo bufo"


# ------------------------------------------------------------ providers and service


def test_mock_is_deterministic_and_labelled() -> None:
    a = MockProvider().suggest(jpeg(), "larvae", allowed("larvae"))
    b = MockProvider().suggest(jpeg(), "larvae", allowed("larvae"))
    assert a.suggestions == b.suggestions
    assert a.suggestions[0].reason.startswith("Demo AI (mock)")


def test_mock_sometimes_invents_labels_which_the_gate_drops() -> None:
    dropped = 0
    for i in range(40):
        out = service.suggest(jpeg((i * 6 % 255, 80, 40)), "adult_mosquito", provider=MockProvider())
        dropped += len(out["dropped"])
        assert all(s["label"] in allowed("adult_mosquito") for s in out["suggestions"])
    assert dropped > 0


def test_dead_birds_never_reach_a_provider() -> None:
    provider = FixedProvider([Suggestion("x", 0.5, "y")])
    with pytest.raises(service.NeverAnalysed):
        service.suggest(jpeg(), "dead_bird", provider=provider)
    assert provider.calls == 0


def test_provider_failure_means_answer_manually() -> None:
    out = service.suggest(jpeg(), "larvae", provider=FailingProvider())
    assert out == {"available": False, "error": "down", "suggestions": [], "dropped": []}


def test_predator_suggestions_are_checked_against_gbif() -> None:
    provider = FixedProvider([Suggestion("Pelophylax perezi", 0.8, "Green frog on a stone")])
    out = service.suggest(jpeg(), "predator", lat=59.9, lon=10.8, provider=provider, gbif_fetch=lambda p: {"count": 0})
    assert out["suggestions"][0]["plausibility"]["status"] == "implausible"
    out = service.suggest(jpeg(), "predator", lat=40.2, lon=-8.4, provider=provider, gbif_fetch=lambda p: {"count": 125})
    assert out["suggestions"][0]["plausibility"]["status"] == "plausible"


def test_gbif_unreachable_is_unchecked(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import httpx

    monkeypatch.setattr(gbif, "CACHE_FILE", tmp_path / "c.json")

    def boom(_: dict) -> dict:
        raise httpx.ConnectError("offline")

    assert gbif.plausibility("Bufo bufo", 1.0, 2.0, fetch=boom)["status"] == "unchecked"


# ------------------------------------------------------------ keys


def test_larva_key() -> None:
    assert run_key("larvae", {"posture": "flat"}) == "anopheles_type"
    assert run_key("larvae", {"posture": "angled"}) == "culex_or_aedes_type"
    assert run_key("larvae", {"posture": "unsure"}) is None
    assert run_key("larvae", {}) is None


def test_adult_key_and_disagreement() -> None:
    key = run_key("adult_mosquito", {"stripes": "yes", "thorax_line": "yes"})
    assert key == "striped_aedes_type"
    assert run_key("adult_mosquito", {"stripes": "no", "colour": "yes"}) == "plain_culex_type"
    assert compare(key, "striped_aedes_type") == "agree"
    assert compare(key, "plain_culex_type") == "disagree"
    assert compare(None, "plain_culex_type") == "incomplete"
    out = service.suggest(jpeg(), "adult_mosquito", key_result=key, provider=FixedProvider([Suggestion("plain_culex_type", 0.6, "Brown body")]))
    assert out["key_vs_vision"] == "disagree"


def test_key_results_are_allowed_labels() -> None:
    from api.ai.keys import load_key

    for result in load_key("adult_mosquito")["results"]:
        assert result in allowed("adult_mosquito")


# ------------------------------------------------------------ HTTP


def test_ai_endpoints(client: TestClient, site: dict) -> None:
    assert client.get("/api/ai/status").json()["mock"] is True
    res = client.post("/api/ai/suggest", params={"finding_type": "larvae", "site_id": "C1"}, files={"file": ("c.jpg", jpeg(), "image/jpeg")})
    assert res.status_code == 200
    body = res.json()
    assert body["mock"] is True and body["suggestions"]
    res = client.post("/api/ai/suggest", params={"finding_type": "dead_bird"}, files={"file": ("c.jpg", jpeg(), "image/jpeg")})
    assert res.status_code == 400 and "never analysed" in res.json()["detail"]


def test_anthropic_provider_request_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    from api.ai.anthropic_provider import AnthropicProvider, _Answer

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    provider = AnthropicProvider()
    captured: dict = {}

    def parse(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=_Answer(label="larvae_present", confidence=0.8, reason="Wrigglers"),
                               usage=SimpleNamespace(input_tokens=900, output_tokens=40))

    provider._client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    out = provider.suggest(jpeg(), "larvae", allowed("larvae"))
    assert captured["model"] == "claude-opus-5"
    assert captured["output_format"] is _Answer
    assert captured["fallbacks"] == "default"
    content = captured["messages"][0]["content"]
    assert content[0]["type"] == "image" and "larvae_present" in content[1]["text"]
    assert out.suggestions[0].label == "larvae_present" and out.input_tokens == 900


def test_anthropic_refusal_becomes_manual(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    from api.ai.anthropic_provider import AnthropicProvider

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    provider = AnthropicProvider()
    provider._client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
        parse=lambda **_: SimpleNamespace(stop_reason="refusal", parsed_output=None, usage=None))))
    assert service.suggest(jpeg(), "larvae", provider=provider)["available"] is False


def test_gemini_requires_explicit_model(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from api.ai.gemini_provider import GeminiProvider

    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    with pytest.raises(ProviderError):
        GeminiProvider()
