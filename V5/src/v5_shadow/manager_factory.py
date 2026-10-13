"""M16 production assembly boundary.

This layer constructs the frozen owner classes. It does not accept service
factories or simulated owner callbacks.
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


def build_manager_jobs(*, config: M16RuntimeConfig, observation_reader: Any):
    if observation_reader is None:
        raise BindingMissing('M16_OBSERVATION_READER_MISSING')
    if not config.runtime_root.is_absolute():
        raise BindingMissing('M16_RUNTIME_ROOT_NOT_ABSOLUTE')

    loaded = load_owner(config.owner_closure)
    components = loaded['components']

    materials = components.material_store_class(config.runtime_root / 'materials')
    store = components.store_class(config.runtime_root)
    provider = components.provider_class(material_store=materials)
    service = components.service_class(
        store,
        observation_reader,
        provider,
        material_store=materials,
    )
    return ManagerJobs(service=service)
