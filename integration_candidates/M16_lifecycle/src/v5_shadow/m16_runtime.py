"""Explicit isolated startup for the existing M16 owner, never a second worker.

Construction initializes one private store. GET never assembles or submits a job.
The input digest pins transport bytes only; original owner contracts alone decide
input identity, cutoff, safety, and research eligibility.
"""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
from typing import Any

from .manager_factory import M16RuntimeConfig, build_manager_jobs
from .manager_loader import OwnerClosure, PREFIX, load_owner

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST_SHA256 = '608ba375bd4402550aa083b330b1f23efa42de3dd340aab8935dc884e1827209'
DEPENDENCY_MANIFEST_SHA256 = '4fa44cbe32992f70cfcec6193e052a9288c87447770694478e2d79c72e3aa210'
MAX_INPUT_BYTES = 8 * 1024 * 1024


def closure() -> OwnerClosure:
    supplemental = ROOT / 'source' / PREFIX / 'v4/manager_research/DEPENDENCY_MANIFEST.json'
    if supplemental.is_symlink() or sha256(supplemental.read_bytes()).hexdigest() != DEPENDENCY_MANIFEST_SHA256:
        raise ValueError('M16_DEPENDENCY_MANIFEST_HASH')
    return OwnerClosure(ROOT / 'source' / PREFIX,
                        ROOT / 'source/SOURCE_MANIFEST.json', SOURCE_MANIFEST_SHA256)


class PinnedObservationReader:
    """Read the original stage observation object without inventing provenance."""
    def __init__(self, path: Path | None, expected_sha256: str | None):
        if (path is None) != (expected_sha256 is None):
            raise ValueError('M16_INPUT_PATH_AND_SHA_REQUIRED_TOGETHER')
        if path is not None and not path.is_absolute():
            raise ValueError('M16_INPUT_PATH_NOT_ABSOLUTE')
        if expected_sha256 is not None and re.fullmatch('[0-9a-f]{64}', expected_sha256) is None:
            raise ValueError('M16_INPUT_SHA_INVALID')
        self.path = path
        self.expected_sha256 = expected_sha256

    def read(self, target_trade_date: str) -> Any:
        # Only the manifest-bound original ContractError is caught by the owner.
        contracts = importlib.import_module('m16_owner_manager_research.contracts')
        if self.path is None:
            return None
        try:
            if any(p.is_symlink() for p in (self.path, *self.path.parents)):
                raise ValueError('M16_INPUT_SYMLINK_REFUSED')
            with self.path.open('rb') as handle:
                raw = handle.read(MAX_INPUT_BYTES + 1)
            if len(raw) > MAX_INPUT_BYTES:
                raise ValueError('M16_INPUT_TOO_LARGE')
            if sha256(raw).hexdigest() != self.expected_sha256:
                raise ValueError('M16_INPUT_BYTES_CHANGED')
            value = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('M16_INPUT_NONFINITE')))
            # Validate, but return untouched fields. The service normalises again.
            normalised = contracts.normalise_observation_input(value)
            if normalised['target_trade_date'] != target_trade_date:
                raise ValueError('STAGE_OBSERVATION_TARGET_DATE_MISMATCH')
            return value
        except (OSError, ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, contracts.ContractError):
                raise
            # Do not expose file paths, supplied text, or secret-like exceptions.
            code = str(exc) if str(exc).startswith(('M16_INPUT_', 'STAGE_OBSERVATION_')) else 'M16_INPUT_UNREADABLE'
            raise contracts.ContractError(code) from None


def create_app(*, runtime_root: Path, input_path: Path | None = None,
               input_sha256: str | None = None, producer_enabled: bool = False):
    """One owner per app; mutation opt-in is deployment configuration, not input."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from .m16_router import create_manager_research_router

    reader = PinnedObservationReader(input_path, input_sha256)
    jobs = build_manager_jobs(config=M16RuntimeConfig(runtime_root, closure()),
                              observation_reader=reader)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            jobs.close()

    app = FastAPI(title='V5 M16 isolated research jobs', lifespan=lifespan)
    app.state.manager_jobs = jobs
    app.state.producer_enabled = producer_enabled

    @app.middleware('http')
    async def producer_gate(request: Request, call_next):
        if request.method not in {'GET', 'HEAD'} and not producer_enabled:
            return JSONResponse(status_code=403, content={'detail': 'M16_PRODUCER_DISABLED'})
        return await call_next(request)

    app.include_router(create_manager_research_router(jobs))
    return app


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--input', dest='input_path', type=Path)
    parser.add_argument('--input-sha256')
    parser.add_argument('--port', type=int, default=8816)
    parser.add_argument('--enable-producer', action='store_true',
                        help='Allow explicit POST jobs using the original public providers; requires separate operating authorization.')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('port must be in 1..65535')
    app = create_app(runtime_root=args.runtime_root, input_path=args.input_path,
                     input_sha256=args.input_sha256, producer_enabled=args.enable_producer)
    import uvicorn
    try:
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
    finally:
        app.state.manager_jobs.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
