"""M16 thin facade over the frozen manager research owner service.

This module owns only V5 boundary naming.  It does not implement a second job
engine, identity generator, store commit path, or research algorithm.  The
frozen ManagerResearchJobService remains the lifecycle owner.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol


class ManagerResearchOwner(Protocol):
    def ensure(self, target_trade_date: str, *, force: bool = False) -> Mapping[str, Any]: ...
    def get(self, target_trade_date: str) -> Mapping[str, Any]: ...
    def retry(self, target_trade_date: str) -> Mapping[str, Any]: ...
    def job(self, job_id: str, target_trade_date: str | None = None) -> Mapping[str, Any]: ...
    def cancel(self, job_id: str, target_trade_date: str | None = None) -> Mapping[str, Any]: ...
    def ensure_events(self, target_trade_date: str, *, force: bool = False) -> Mapping[str, Any]: ...
    def close(self) -> None: ...


class ManagerJobs:
    """M16 API boundary delegating to ManagerResearchJobService.

    The real constructor receives the already assembled frozen owner service.
    It intentionally does not accept client supplied observations, providers,
    cutoff values, generations, attempts, or direct commit callbacks.
    """

    def __init__(self, *, service: ManagerResearchOwner):
        self._service = service

    def ensure(self, target_trade_date: str, *, force: bool = False) -> Mapping[str, Any]:
        return self._service.ensure(target_trade_date, force=force)

    def get(self, target_trade_date: str) -> Mapping[str, Any]:
        return self._service.get(target_trade_date)

    def retry(self, target_trade_date: str) -> Mapping[str, Any]:
        return self._service.retry(target_trade_date)

    def job(self, job_id: str, target_trade_date: str | None = None) -> Mapping[str, Any]:
        return self._service.job(job_id, target_trade_date=target_trade_date)

    def cancel(self, job_id: str, target_trade_date: str | None = None) -> Mapping[str, Any]:
        return self._service.cancel(job_id, target_trade_date=target_trade_date)

    def ensure_events(self, target_trade_date: str, *, force: bool = False) -> Mapping[str, Any]:
        return self._service.ensure_events(target_trade_date, force=force)

    def close(self) -> None:
        self._service.close()
