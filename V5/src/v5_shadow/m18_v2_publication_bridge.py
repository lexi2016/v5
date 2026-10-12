"""Bounded M18 v2 publication bridge.

Consumes an already-built v2 bundle and publishes only descriptors/chunks through
module_artifacts. It never builds bundles, runs owners, or performs collection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from .module_artifacts import publish_generation

ROUTE = "/api/v4/manager/m18/v2"


def descriptor_from_bundle(reader, identity, bundle_meta):
    """Create a small API object; large response bytes stay in v2 pages."""
    if bundle_meta.get("identity") != identity:
        raise ValueError("M18_IDENTITY_MISMATCH")
    return {
        "schema_version": "v5.m18.v2.descriptor.v1",
        "identity": identity,
        "run_id": identity["run_id"],
        "target_date": identity["target_date"],
        "generation_id": bundle_meta["generation_id"],
        "profile_sha256": bundle_meta["profile_sha256"],
        "pages_route": ROUTE + "/pages",
        "status": "READY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def publish_m18_descriptor(config, descriptor, *, expected_generation):
    record = {
        "schema_version": "v5.module_response.v1",
        "module_id": config["module_id"],
        "release_id": config["release_id"],
        "path": ROUTE,
        "query": {"run_id": descriptor["run_id"]},
        "payload": descriptor,
        "payload_sha256": __import__("v5_shadow.digests", fromlist=["sha256_json"]).sha256_json(descriptor),
        "source_input_sha256": descriptor["profile_sha256"],
        "data_kind": "OWNER_RESULT",
        "generated_at": descriptor["generated_at"],
        "status_code": 200,
    }
    return publish_generation(config, [record], expected_generation=expected_generation)
