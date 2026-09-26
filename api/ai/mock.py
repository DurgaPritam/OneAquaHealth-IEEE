"""Deterministic demo provider. It does not look at the photo content.

The label is chosen from the allowed list by hashing the image bytes, so the
same photo always gets the same answer. About one photo in five also yields an
out-of-list label, so the validation gate and its UI can be demonstrated.
"""

from __future__ import annotations

import hashlib
import time

from api.ai.base import ProviderResult, Suggestion

INVENTED = {
    "larvae": "Culex pipiens larva",
    "adult_mosquito": "Aedes albopictus (confirmed)",
    "predator": "Pelophylax kl. esculentus",
    "habitat": "West Nile hotspot",
}


class MockProvider:
    name = "mock"
    model = "mock-deterministic-1"

    def suggest(self, image: bytes, finding_type: str, allowed: list[str]) -> ProviderResult:
        start = time.perf_counter()
        digest = hashlib.sha256(image + finding_type.encode()).digest()
        choices = [label for label in allowed if label != "not_sure"] or ["not_sure"]
        label = choices[digest[0] % len(choices)]
        confidence = round(0.5 + (digest[1] / 255) * 0.45, 2)
        reason = "Demo AI (mock): placeholder suggestion, the photo was not analysed."
        suggestions = [Suggestion(label, confidence, reason)]
        if digest[2] % 5 == 0 and finding_type in INVENTED:
            suggestions.append(Suggestion(INVENTED[finding_type], 0.9, "Demo AI (mock): invented label to show the validation gate."))
        return ProviderResult(suggestions, self.name, self.model, (time.perf_counter() - start) * 1000)
