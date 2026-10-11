"""M16 owner closure loading contract.

The loader does not bypass the frozen manifest guard.  The integrator must
provide a validated private closure root containing the original owner blobs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SourceClosureError(RuntimeError):
    pass


@dataclass(frozen=True)
class OwnerClosure:
    root: Path
    manifest_sha256: str


def require_owner_closure(closure: OwnerClosure) -> OwnerClosure:
    if not closure.root.exists():
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_ROOT_MISSING")
    if not closure.manifest_sha256:
        raise SourceClosureError("MANAGER_SOURCE_CLOSURE_MANIFEST_MISSING")
    return closure
