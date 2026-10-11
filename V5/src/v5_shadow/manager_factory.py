"""M16 production assembly boundary.

This factory owns assembly, not research logic. Missing real owner bindings fail
closed; simulated providers are not production defaults.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manager_jobs import ManagerJobs
from .manager_loader import OwnerClosure, load_owner


class BindingMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class M16RuntimeConfig:
    runtime_root: Path
    owner_closure: OwnerClosure


def build_manager_jobs(*, config: M16RuntimeConfig):
    loaded = load_owner(config.owner_closure)
    builder = loaded.get('factory')
    if not callable(builder):
        raise BindingMissing('M16_OWNER_FACTORY_NOT_BOUND')
    service = builder(runtime_root=config.runtime_root)
    if service is None:
        raise BindingMissing('M16_OWNER_SERVICE_UNAVAILABLE')
    return ManagerJobs(service=service)
