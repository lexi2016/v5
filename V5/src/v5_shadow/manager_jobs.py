"""M16 isolated manager research job entry.

This module is deliberately isolated from shared router/UI code.  Production
assembly must provide the frozen V4 owner closure (service/store/provider).
Only the boundary orchestration lives here.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Protocol
import json


class M16Store(Protocol):
    def ensure_job(self, job: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def commit_result(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def read_product(self, **kwargs: Any) -> Mapping[str, Any]: ...


class M16Observer(Protocol):
    def read(self, target_trade_date: str) -> Mapping[str, Any]: ...


class M16Provider(Protocol):
    provider_id: str
    def collect(self, *, target_trade_date: str, cutoff_at: str,
                observation: Mapping[str, Any]) -> Mapping[str, Any]: ...


class M16ResearchService(Protocol):
    def run(self, **kwargs: Any) -> Mapping[str, Any]: ...


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class M16Identity:
    target_trade_date: str
    input_identity: str
    source_sha256: str | None
    generation: int
    attempt: int


class ManagerJobs:
    """Default M16 lifecycle coordinator.

    The constructor accepts real owner implementations.  SIMULATED tests may
    inject doubles, but the default path never invents provider/store objects.
    """

    def __init__(self, *, store: M16Store, observer: M16Observer,
                 provider: M16Provider, service: M16ResearchService):
        self._store = store
        self._observer = observer
        self._provider = provider
        self._service = service

    def ensure(self, *, target_trade_date: str, cutoff_at: str,
               generation: int = 0, attempt: int = 0) -> Mapping[str, Any]:
        observation = self._observer.read(target_trade_date)
        identity = _digest(observation)
        job = {
            "target_trade_date": target_trade_date,
            "cutoff_at": cutoff_at,
            "input_identity": identity,
            "source_sha256": observation.get("source_sha256"),
            "generation": generation,
            "attempt": attempt,
            "provider_id": self._provider.provider_id,
            "state": "QUEUED",
        }
        existing = self._store.ensure_job(job)
        if existing.get("state") in {"READY", "PARTIAL_WITH_ROWS"}:
            return existing
        result = self._service.run(
            target_trade_date=target_trade_date,
            cutoff_at=cutoff_at,
            observation=observation,
            provider=self._provider,
        )
        return self._store.commit_result(
            job=job,
            product=result.get("product"),
            receipt=result.get("receipt"),
        )

    def read(self, *, target_trade_date: str,
             input_identity: str) -> Mapping[str, Any]:
        """Read-only boundary.  No ensure/provider/recovery is allowed here."""
        return self._store.read_product(
            target_trade_date=target_trade_date,
            input_identity=input_identity,
        )
