"""V5 P0 explicit module registry.

This layer only declares integration ownership. It does not execute strategies.
Missing runtime adapters remain NOT_READY instead of being silently skipped.
READY denotes a callable adapter, never verified current-day business inputs.
"""
from dataclasses import dataclass
from typing import Callable, Mapping


@dataclass(frozen=True)
class ModuleRegistration:
    module_id: str
    owner_entry: str | None
    runtime: str
    status: str
    dependencies: tuple[str, ...] = ()


# Stable P0 registration order. Lane != module identity.
MODULE_REGISTRY: tuple[ModuleRegistration, ...] = (
    ModuleRegistration("M01_A_MARKET", "m01_a_source", "source_bundle", "READY"),
    ModuleRegistration("M02_HK_MARKET", "m02_hk_source", "source_bundle", "READY"),
    ModuleRegistration("M03_US_MARKET", "m03_us_source", "source_bundle", "READY"),
    ModuleRegistration("M04_RESEARCH_ARCHIVE", "research_archive", "daily_owner_adapters", "NOT_READY"),
    ModuleRegistration("M05_A_PRESELECTION", "m05_a_preselection", "source_bundle", "READY"),
    ModuleRegistration("M06_HK_PRESELECTION", "p0_hk_preselection", "daily_tick", "READY"),
    ModuleRegistration("M07_A_STAGE", "a_stage", "daily_owner_adapters", "READY"),
    ModuleRegistration("M08_HK_STAGE", "hk_stage", "daily_owner_adapters", "NOT_READY"),
    ModuleRegistration("M09_A_CLOSE_REVIEW", "a_close_review", "daily_owner_adapters", "READY"),
    ModuleRegistration("M10_HK_CLOSE_REVIEW", "hk_close_review", "daily_owner_adapters", "NOT_READY"),
    ModuleRegistration("M11_INTRADAY_RESEARCH", "research_review_daily.generate", "m11_readonly", "CALLABLE_CANDIDATE_REQUIRES_INPUT"),
    ModuleRegistration("M12_VIDEO_FUPAN", "m12_daily.run_daily", "m12_readonly", "CALLABLE_CANDIDATE_REQUIRES_INPUT"),
    ModuleRegistration("M13_ANNOUNCEMENT", "announcement_analysis", "daily_owner_adapters", "READY"),
    ModuleRegistration("M14_REBOUND", "rebound_shadow", "daily_owner_adapters", "READY"),
    ModuleRegistration("M15_US_MAPPING", "us_mapping", "daily_owner_adapters", "READY"),
    ModuleRegistration("M16_PUBLIC_RESEARCH", "manager_public_research", "daily_owner_adapters", "NOT_READY"),
    ModuleRegistration("M17_CLOSE_RECAPTURE", "daily_close_recapture", "daily_tick", "READY"),
    ModuleRegistration("M18_MANAGER", "manager_plan", "m18_offline_v2", "READY", ("M13_ANNOUNCEMENT", "M14_REBOUND", "M15_US_MAPPING")),
)


def registry_by_id() -> dict[str, ModuleRegistration]:
    return {item.module_id: item for item in MODULE_REGISTRY}


def registration_snapshot() -> list[dict]:
    return [
        {
            "module_id": item.module_id,
            "owner_entry": item.owner_entry,
            "runtime": item.runtime,
            "status": item.status,
            "dependencies": list(item.dependencies),
        }
        for item in MODULE_REGISTRY
    ]


def validate_registry() -> None:
    ids = [item.module_id for item in MODULE_REGISTRY]
    if len(ids) != len(set(ids)):
        raise ValueError("MODULE_ID_DUPLICATE")
    known = set(ids)
    for item in MODULE_REGISTRY:
        if any(dep not in known for dep in item.dependencies):
            raise ValueError("MODULE_DEPENDENCY_UNKNOWN")
