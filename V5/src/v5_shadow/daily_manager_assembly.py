"""Seal actual post-owner inputs/cutoff once, then reuse original manager owner."""

import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
import re
from pathlib import Path

from v5_shadow.digests import sha256_json
from v5_shadow.module_api import _open_directory, _read_at
from v5_shadow.module_artifacts import _directory, _write_once
from v5_shadow.run_ledger import locked, _read, _write, MARKER


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RUN32 = re.compile(r"^[0-9a-f]{32}$")


def _require_hex64(value, name):
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(name)
    return value


def _require_run(value):
    if not isinstance(value, str) or not _RUN32.fullmatch(value):
        raise ValueError("DAILY_MANAGER_RUN")
    return value


def _validate_announcement_binding(binding, target):
    if not isinstance(binding, dict):
        raise ValueError("DAILY_MANAGER_ANNOUNCEMENT_BINDING")

    if binding.get("target_date") != target:
        raise ValueError("DAILY_MANAGER_ANNOUNCEMENT_TARGET")

    _require_hex64(
        binding.get("binding_sha256"),
        "DAILY_MANAGER_ANNOUNCEMENT_BINDING_HASH",
    )

    if not isinstance(binding.get("publication_date"), str):
        raise ValueError(
            "DAILY_MANAGER_ANNOUNCEMENT_PUBLICATION"
        )

    if "revision_manifest_sha256" in binding:
        _require_hex64(
            binding["revision_manifest_sha256"],
            "DAILY_MANAGER_ANNOUNCEMENT_REVISION_HASH",
        )

    return copy.deepcopy(binding)


def _validate_rebound_owner(value):
    if not isinstance(value, dict):
        raise ValueError("DAILY_MANAGER_REBOUND_OWNER")

    reference = value.get("reference")
    if not isinstance(reference, dict):
        raise ValueError(
            "DAILY_MANAGER_REBOUND_REFERENCE"
        )

    expected = {
        "run_id",
        "artifact_sha256",
        "manifest_sha256",
        "receipt_sha256",
    }

    if set(reference) != expected:
        raise ValueError(
            "DAILY_MANAGER_REBOUND_REFERENCE_KEYS"
        )

    _require_run(reference["run_id"])

    for key in (
        "artifact_sha256",
        "manifest_sha256",
        "receipt_sha256",
    ):
        _require_hex64(
            reference[key],
            "DAILY_MANAGER_REBOUND_" + key,
        )

    return copy.deepcopy(value)


def _validate_rebound_reference(reference):
    owner = {
        "root": reference["root"],
        "reference": reference["reference"],
    }
    return _validate_rebound_owner(owner)


def _merge_announcement_binding(request, lane_binding, target):
    existing = request.get(
        "announcement_offline_owner"
    )

    existing = (
        _validate_announcement_binding(
            existing,
            target,
        )
        if existing is not None
        else None
    )

    lane_binding = (
        _validate_announcement_binding(
            lane_binding,
            target,
        )
        if lane_binding is not None
        else None
    )

    if existing is not None and lane_binding is not None:
        if existing != lane_binding:
            raise ValueError(
                "DAILY_MANAGER_ANNOUNCEMENT_BINDING_CONFLICT"
            )

    request["announcement_offline_owner"] = (
        lane_binding
        if lane_binding is not None
        else existing
    )


def product_reference(row):
    state = row.get("state") or {}
    attempts = state.get("attempts") or []
    return (
        attempts[-1].get("product_reference")
        if attempts
        and attempts[-1].get("readback_verified") is True
        else None
    )


def assemble_manager_request(
    template,
    lanes,
    ledger_root,
    registration,
):
    from v5_shadow.manager_plan import _snapshot

    now = datetime.now(timezone.utc)

    target = now.astimezone(
        timezone(timedelta(hours=8))
    ).strftime("%Y%m%d")

    if template["target_date"] != target:
        raise ValueError(
            "DAILY_MANAGER_TEMPLATE_TARGET"
        )

    request = copy.deepcopy(template)

    request.update(
        action="refresh",
        view="auto",
        selection_date=None,
        announcement_date=None,
    )

    files = {
        name: raw
        for name, raw in _snapshot(
            request["inputs"]["manager"]
        ).items()
        if not name.startswith(
            "us_mapping_research/"
        )
    }

    # Historical template observation is stale input.
    # A verified rebound lane below is a separate contract.
    request.pop(
        "rebound_observation",
        None,
    )

    if request.get("rebound_owner") is not None:
        request["rebound_owner"] = (
            _validate_rebound_owner(
                request["rebound_owner"]
            )
        )

    if request.get("announcement_offline_owner") is not None:
        request["announcement_offline_owner"] = (
            _validate_announcement_binding(
                request["announcement_offline_owner"],
                target,
            )
        )

    for row in lanes:
        ref = product_reference(row)

        if not ref:
            continue

        lane = row["lane"]

        if lane == "us_mapping":
            if ref["target_date"] != target:
                raise ValueError(
                    "DAILY_MANAGER_US_TARGET"
                )

            run = _require_run(
                ref["run_id"]
            )

            root = _open_directory(
                ref["manager_output_root"]
            )

            day = None
            runs = None

            try:
                parent = os.open(
                    "us_mapping_research",
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_NOFOLLOW,
                    dir_fd=root,
                )

                try:
                    day = os.open(
                        target,
                        os.O_RDONLY
                        | os.O_DIRECTORY
                        | os.O_NOFOLLOW,
                        dir_fd=parent,
                    )
                finally:
                    os.close(parent)

                runs = os.open(
                    "runs",
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_NOFOLLOW,
                    dir_fd=day,
                )

                raw = _read_at(
                    runs,
                    None,
                    run + ".json",
                )

                daily = json.loads(raw)

                unsigned = dict(daily)
                digest = unsigned.pop(
                    "artifact_sha256"
                )

                if (
                    digest
                    != ref["artifact_sha256"]
                    or sha256_json(unsigned)
                    != digest
                    or daily["run_id"] != run
                ):
                    raise ValueError(
                        "DAILY_MANAGER_US_ARTIFACT"
                    )

                pointer = _read_at(
                    day,
                    None,
                    "latest.json",
                )

                head = json.loads(pointer)

                if (
                    head["run_id"] != run
                    or head["artifact_sha256"]
                    != digest
                ):
                    raise ValueError(
                        "DAILY_MANAGER_US_HEAD_CHANGED"
                    )

                prefix = (
                    "us_mapping_research/"
                    + target
                    + "/"
                )

                files[
                    prefix
                    + "runs/"
                    + run
                    + ".json"
                ] = raw

                files[
                    prefix + "latest.json"
                ] = pointer

            finally:
                for fd in (
                    runs,
                    day,
                    root,
                ):
                    if fd is not None:
                        os.close(fd)

        elif lane == "announcement":
            binding = ref.get("binding")
            if binding is not None:
                _merge_announcement_binding(
                    request,
                    binding,
                    target,
                )

        elif lane == "rebound":
            if ref.get("reference"):
                rebound_owner = (
                    _validate_rebound_reference(ref)
                )

                # New explicit owner contract.
                request["rebound_owner"] = (
                    rebound_owner
                )

                # Compatibility view for legacy
                # verified rebound lane consumers.
                # This does not mean formal rebound
                # qualification or observation.
                request["rebound_observation"] = {
                    "root": rebound_owner["root"],
                    "reference": copy.deepcopy(
                        rebound_owner["reference"]
                    ),
                }

    hashes = {
        name: hashlib.sha256(raw).hexdigest()
        for name, raw in files.items()
    }

    digest = sha256_json(hashes)

    root = _open_directory(
        ledger_root
    )

    staging = None
    version = None

    try:
        if (
            _read_at(
                root,
                None,
                ".v5-daily-run-ledger",
            )
            != MARKER
        ):
            raise ValueError(
                "DAILY_MANAGER_LEDGER_MARKER"
            )

        staging = _directory(
            root,
            "manager_inputs",
        )

        version = _directory(
            staging,
            digest,
        )

        for name, raw in files.items():
            parent = os.dup(version)

            try:
                for component in Path(name).parts[:-1]:
                    child = _directory(
                        parent,
                        component,
                    )
                    os.close(parent)
                    parent = child

                _write_once(
                    parent,
                    Path(name).name,
                    raw,
                )

            finally:
                os.close(parent)

    finally:
        for fd in (
            version,
            staging,
            root,
        ):
            if fd is not None:
                os.close(fd)

    request["inputs"]["manager"] = {
        "root": str(
            Path(ledger_root)
            / "manager_inputs"
            / digest
        ),
        "files": hashes,
    }

    request.pop("now", None)

    identity = dict(
        registration,
        lane="manager_plan",
        target_date=target,
        input_sha256=sha256_json(request),
        research_cutoff=(
            target[:4]
            + "-"
            + target[4:6]
            + "-"
            + target[6:]
            + "T08:45:00+08:00"
        ),
    )

    with locked(
        ledger_root,
        identity,
    ) as (fd, key):

        name = "request-" + key + ".json"

        saved = _read(
            fd,
            name,
        )

        if saved is not None:
            return saved

        request["now"] = now.isoformat()

        _write(
            fd,
            name,
            request,
        )

        return request
