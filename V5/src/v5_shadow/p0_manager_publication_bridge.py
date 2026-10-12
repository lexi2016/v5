"""P0 bounded publication bridge.

Consumes an already-built manager/v2 result only. It does not run managers,
owners, collectors or trading. v2 generation identity and module publication
identity remain separate.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .digests import sha256_json
from .module_artifacts import publish_generation
from .contracts import sha

ROUTE = "/api/v4/manager/research/workspace"


def build_manager_record(*, config, payload, source_input_sha256, date, view="auto"):
    if not isinstance(payload, dict):
        raise ValueError("MANAGER_PAYLOAD_REQUIRED")
    if not isinstance(source_input_sha256, str):
        raise ValueError("MANAGER_SOURCE_IDENTITY_REQUIRED")
    sha(source_input_sha256)
    query = {"date": date, "view": view}
    return {
        "schema_version": "v5.module_response.v1",
        "module_id": config["module_id"],
        "release_id": config["release_id"],
        "path": ROUTE,
        "query": query,
        "payload": payload,
        "payload_sha256": sha256_json(payload),
        "source_input_sha256": source_input_sha256,
        "data_kind": "OWNER_RESULT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_code": 200,
    }


def publish_saved_manager_result(*, config, payload, source_input_sha256, expected_generation, date, view="auto"):
    record = build_manager_record(
        config=config,
        payload=payload,
        source_input_sha256=source_input_sha256,
        date=date,
        view=view,
    )
    return publish_generation(config, [record], expected_generation=expected_generation)
