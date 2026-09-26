"""Transaction Bundle assembly with deterministic urn:uuid full URLs."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from api.fhir import codes as c

Resource = dict[str, Any]

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, c.CANONICAL)


def urn(kind: str, key: str) -> str:
    """Stable urn:uuid for a resource, so re-exports of the same records give the same full URLs."""
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, f'{kind}/{key}')}"


class TransactionBuilder:
    """Collects entries once per full URL and emits a FHIR R4 transaction Bundle."""

    def __init__(self, bundle_key: str) -> None:
        self.bundle_key = bundle_key
        self.entries: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def add(self, full_url: str, resource: Resource, if_none_exist: Optional[str] = None) -> str:
        if full_url in self._seen:
            return full_url
        self._seen.add(full_url)
        request: dict[str, str] = {"method": "POST", "url": resource["resourceType"]}
        if if_none_exist:
            request["ifNoneExist"] = if_none_exist
        self.entries.append({"fullUrl": full_url, "resource": resource, "request": request})
        return full_url

    def __contains__(self, full_url: str) -> bool:
        return full_url in self._seen

    def build(self, timestamp: str) -> Resource:
        synthetic = any(_is_synthetic(e["resource"]) for e in self.entries)
        bundle: Resource = {
            "resourceType": "Bundle",
            "identifier": {"system": f"{c.CANONICAL}/sid/bundle", "value": self.bundle_key},
            "type": "transaction",
            "timestamp": timestamp,
            "entry": self.entries,
        }
        if synthetic:
            bundle["meta"] = {"tag": [dict(c.SYNTHETIC_TAG)]}
        return bundle


def _is_synthetic(resource: Resource) -> bool:
    return any(t.get("code") == "synthetic" and t.get("system") == c.AS for t in resource.get("meta", {}).get("tag", []))


def identifier_query(system: str, value: str) -> str:
    return f"identifier={system}|{value}"
