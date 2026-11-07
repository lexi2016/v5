"""Owner-internal stage implementation. NOT an admission or standalone run API.

The caller must already own the reviewed source/attempt, original locks, monitor,
native runner and original writer. This module neither acquires substitute locks
nor creates authority from caller booleans. Production registration remains absent.
There is deliberately no CLI and no default/live runtime construction.
"""
import gzip
import hashlib
import json
import types
from pathlib import Path
from dataclasses import dataclass, field


def need(ok, message):
    if not ok:
        raise ValueError(message)


def original_provider():
    """Load verified recovered original source in a private namespace, unchanged."""
    p = Path(__file__).resolve().parents[2] / 'handoff/par_daily_chain_repair_20261106/provider/continuation_provider.py'
    raw = p.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == '84feb79cb762e85dea34e4e732feb541e798bd0b0943ff28378f01611d7a3040', 'ORIGINAL_PROVIDER_PIN')
    module = types.ModuleType('compute_kernel_original_provider')
    module.__file__ = str(p)
    exec(compile(raw, str(p), 'exec'), module.__dict__)
    return module


@dataclass
class Attempt:
    """Held by the enclosing owner, including on UNKNOWN; not an auth token."""
    symbol: str
    target: int
    phase: str = 'INPUT_BOUND'
    objects: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    error: BaseException | None = None

    def enter(self, expected, phase, runtime):
        need(self.phase == expected, 'PHASE_OR_NO_RETRY')
        runtime.gate()
        self.phase = phase
        self.events.append(phase)


def advance_stock(attempt, runtime, prior_selection, input_ref, expected_input_sha):
    """Execute actual one-symbol prepare/compute/persist using owner-held services.

    runtime is PRIVATE OWNER CONTROL FLOW, not a browser/JSON supplied object.
    Caller supplies reviewed exact refs, never inferred self-reported approval.
    No locks/monitor/connection lifecycle is released here on failure. A retained
    Attempt keeps original returned objects and exception for owner's E1 handling.
    Test doubles must be explicitly reported as simulated, not real native runs.
    """
    need(attempt.phase == 'INPUT_BOUND', 'PHASE_OR_NO_RETRY')
    need(input_ref['sha256'] == expected_input_sha, 'EXTERNAL_INPUT_PIN')
    # This check is before STARTED, prepare, formula or writer. A previous unknown
    # attempt is not equivalent to a completed result.
    existing = runtime.completed(attempt.symbol, attempt.target, input_ref)
    if existing is not None:
        runtime.verify_completed(existing, attempt.symbol, attempt.target, input_ref)
        attempt.objects['completed'] = existing
        attempt.phase = 'REUSE_COMPLETED_NO_RECOMPUTE'
        return existing
    runtime.verify_inputs(prior_selection, input_ref, expected_input_sha)
    try:
        attempt.enter('INPUT_BOUND', 'STARTED_WRITE', runtime)
        # Enclosing owner supplies its held-FD STARTED obligation implementation.
        attempt.objects['started'] = runtime.started(attempt.symbol, attempt.target)
        attempt.enter('STARTED_WRITE', 'PREPARE_STARTED', runtime)
        if not prior_selection.get('continuation_ref'):
            facts = json.loads(runtime.checked(input_ref))
            need(facts['status'] == 'VERIFIED_NO_VALID_BAR', 'NO_PRIOR_VALID_BAR')
            runtime.checked(facts['no_bar_evidence_ref'])
            prepared = dict(status='RETAINED_NO_VALID_BAR', symbol=attempt.symbol,
                            event_date=prior_selection['event_date'],
                            prior_selection=prior_selection, **runtime.flags)
        else:
            prepared = runtime.provider.prepare(prior_selection['continuation_ref'],
                                                input_ref, expected_input_sha)
        attempt.objects['prepared'] = prepared
        need(prepared['symbol'] == attempt.symbol, 'PREPARED_SYMBOL')
        attempt.enter('PREPARE_STARTED', 'PREPARE_RETURNED', runtime)
        if prepared['status'] == 'RETAINED_NO_VALID_BAR':
            attempt.objects['retained_ref'] = runtime.save('RETAINED.json', prepared)
            attempt.phase = 'RETAINED_NO_VALID_BAR'
            return attempt.objects['retained_ref']
        need(prepared['status'] == 'PREPARED_ONE_SESSION', 'PREPARED_STATUS')
        attempt.enter('PREPARE_RETURNED', 'COMPUTE_STARTED', runtime)
        # Exact original objects, no clone/cross-attempt substitutions.
        row, facts = runtime.compute(prepared['rows'], prepared['context'],
                                     prior_state=prepared['prior_component_state'])
        attempt.objects.update(row=row, facts=facts)
        need(row['event_date'] == str(attempt.target), 'NEW_DATE_EXACT')
        need(facts['historical109_rows_evaluated'] == 0 and
             facts['prior_component_state_reused'] is True, 'LATEST_ONLY_PRIOR_COMPONENTS')
        component = facts['component_state']
        attempt.objects['component'] = component
        before = {k: v for k, v in facts.items() if k != 'component_state'}
        need(facts.pop('component_state') is component, 'COMPONENT_TRANSFER_IDENTITY')
        need(facts == before and 'component_state' not in facts, 'COMPONENT_TRANSFER_ONLY')
        attempt.enter('COMPUTE_STARTED', 'CONTINUATION_STARTED', runtime)
        bundle = original_provider().continuation(prepared, component)
        attempt.objects['bundle'] = bundle
        need(bundle['symbol'] == attempt.symbol and bundle['asof'] == str(attempt.target),
             'CONTINUATION_IDENTITY')
        attempt.enter('CONTINUATION_STARTED', 'PERSIST_STARTED', runtime)
        payload = gzip.compress(json.dumps(bundle, ensure_ascii=False,
                                separators=(',', ':'), allow_nan=False).encode(), mtime=0)
        state_ref = runtime.save('continuation.json.gz', payload)
        attempt.objects['state_ref'] = state_ref
        need(runtime.checked(state_ref) == payload, 'CONTINUATION_READBACK')
        # Provenance is built here, not accepted from a receipt or caller.
        provenance = dict(symbol=attempt.symbol, calculation_asof=str(attempt.target),
                          state_bundle_ref=state_ref, input_provenance=prepared['provenance'],
                          compute_facts=facts, **runtime.flags)
        attempt.objects['provenance'] = provenance
        attempt.enter('PERSIST_STARTED', 'PARQUET_STARTED', runtime)
        # The original native/DB/writer and all writer resource gates remain owned
        # by the caller. Connection scope is deliberately its original context.
        with runtime.connection() as con:
            receipt = runtime.writer.write_stock(con, [row], provenance,
                         runtime.parquet_dir, runtime.mods, runtime.schema, runtime.monitor)
            attempt.objects['receipt'] = receipt
        need(receipt['symbol'] == attempt.symbol and receipt['event_dates'] == [str(attempt.target)] and
             str(receipt['calculation_asof']) == str(attempt.target), 'PARQUET_DATE_IDENTITY')
        need(receipt['field_rows'] == 109 and receipt['metadata_rows'] == 1 and
             receipt['full_objects_context_types_ieee_bits_key_orders_exact'] is True,
             'ORIGINAL_PARQUET_ROUNDTRIP')
        runtime.gate()
        cleanup = runtime.remove_committed_temporary_links(receipt)
        result = dict(status='COMPUTED_SAME_BASIS_NEXT_SESSION_WITH_CONTINUATION',
                      symbol=attempt.symbol, event_date=str(attempt.target),
                      continuation_ref=state_ref,
                      parquet_receipt_ref=runtime.receipt_ref(),
                      temporary_link_cleanup=cleanup, compute_facts=facts, **runtime.flags)
        attempt.objects['success_ref'] = runtime.save('SUCCESS.json', result)
        attempt.phase = 'PERSISTED_AWAIT_OWNER_SEAL_AND_INDEPENDENT_SAMPLE'
        return attempt.objects['success_ref']
    except BaseException as error:
        attempt.error = error
        attempt.phase = 'UNKNOWN_NO_BLIND_RETRY'
        # No exception-path write when locks/resources might be invalid. The
        # existing owner must preserve the obligation/FD, not close it in finally.
        raise


def finalize_reviewed_catalog(runtime, prior_ref, manifest_ref, independent_sample_ref,
                              destination):
    """Actual original metadata overlay, after a separate independent sample.

    Does not re-label an owner manifest, forge sample evidence or update CURRENT.
    Incompatible original/portable statuses must remain a visible error.
    """
    runtime.gate()
    value = runtime.finalizer.build(prior_ref, manifest_ref, independent_sample_ref)
    runtime.gate()
    pin = runtime.finalizer.write_new(destination, value)
    need(json.loads(runtime.checked(pin)) == value, 'CATALOG_READBACK')
    return pin


def select_reviewed_catalog(runtime, args):
    """Invoke unchanged original four-group selector and its locks/resources.

    Its policy, review, full5575, reader, raw-reference and UNKNOWN handling apply.
    This stage neither runs before finalization nor invents a review.
    """
    runtime.gate()
    need(args.execute is True and args.review is not None, 'SELECTION_REVIEW_REQUIRED')
    return runtime.selector.run(args)
