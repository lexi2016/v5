"""Private fresh-process factory for the original, identity-checked M05 store.

Importing this module does not install a loader. build_strict_store must run in
an independent writer/readback process, never in the guarded assembly worker.
No owner source, descriptor, guard or store implementation is changed here.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import sys

from .a_preselection import _FrozenLoader, _source_bytes
from .a_preselection_daily import _context_binding


@dataclass(frozen=True)
class FrozenStoreRuntime:
    store: object
    context: object
    owner: object
    gate: object
    locks: object
    loader: object


def build_strict_store(root, write_gate_context):
    """Load store and context from one verified capsule and bind strict writes."""
    if any(name.split('.')[0] in ('domains', 'infrastructure', 'contracts', 'upstreams')
           for name in sys.modules):
        raise ValueError('M05_WRITER_REQUIRES_FRESH_PROCESS')
    binding = _context_binding(write_gate_context)
    loader = _FrozenLoader(_source_bytes())
    sys.meta_path.insert(0, loader)
    gate = importlib.import_module('infrastructure.scope_gate')
    owner = importlib.import_module('infrastructure.preselection_pool_store')
    locks = importlib.import_module('infrastructure.interprocess_lock')
    if any(module.__loader__ is not loader for module in (gate, owner, locks)):
        raise ValueError('M05_FROZEN_LOADER_IDENTITY_MISMATCH')
    if owner.StoreGateContext is not gate.StoreGateContext:
        raise ValueError('M05_CONTEXT_SOURCE_IDENTITY_MISMATCH')
    binding['control_dir'] = Path(binding['control_dir'])
    binding['expected_root'] = Path(binding['expected_root'])
    context = gate.StoreGateContext(**binding)
    store = owner.PreselectionPoolStore(Path(root), write_gate_context=context,
                                      require_write_gate_context=True)
    runtime = FrozenStoreRuntime(store, context, owner, gate, locks, loader)
    validate_strict_store(runtime)
    return runtime


def validate_strict_store(runtime):
    if not isinstance(runtime.context, runtime.gate.StoreGateContext):
        raise ValueError('M05_WRITE_GATE_CONTEXT_TYPE_REQUIRED')
    if not isinstance(runtime.store, runtime.owner.PreselectionPoolStore):
        raise ValueError('M05_STORE_TYPE_REQUIRED')
    if getattr(runtime.store, '_require_write_gate_context', None) is not True:
        raise ValueError('M05_STORE_STRICT_GATE_REQUIRED')
    if getattr(runtime.store, '_write_gate_context', None) is not runtime.context:
        raise ValueError('M05_STORE_GATE_CONTEXT_MISMATCH')
