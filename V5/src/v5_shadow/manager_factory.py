"""M16 isolated production assembly boundary.

This module deliberately does not provide a fake observation source.  The
application must bind an approved server-owned reader and provider through the
resolver contract.  Missing activity binding fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Any


class BindingMissing(RuntimeError):
    pass


class OwnerFactory(Protocol):
    def __call__(self, *, runtime_root: Path) -> Any: ...


@dataclass(frozen=True)
class M16RuntimeConfig:
    runtime_root: Path


@dataclass(frozen=True)
class M16Bindings:
    service_factory: OwnerFactory


def build_manager_jobs(*, config: M16RuntimeConfig, bindings: M16Bindings):
    """Build the thin M16 facade over the original owner service.

    Store/service/provider construction remains outside the facade and must be
    supplied by an approved binding.  No network, credentials, or fallback
    observation is created here.
    """
    if not callable(bindings.service_factory):
        raise BindingMissing("M16_SERVICE_FACTORY_MISSING")
    from .manager_jobs import ManagerJobs
    service = bindings.service_factory(runtime_root=config.runtime_root)
    if service is None:
        raise BindingMissing("M16_OWNER_SERVICE_UNAVAILABLE")
    return ManagerJobs(service=service)
