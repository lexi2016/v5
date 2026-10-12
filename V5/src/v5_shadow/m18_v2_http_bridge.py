"""Bounded read-only M18 v2 route helpers.

Serves published descriptors and v2 page objects only. It never publishes,
refreshes managers, runs owners, or builds bundles.
"""
from __future__ import annotations

from .m18_offline_v2 import Reader

ROUTE = "/api/v4/manager/m18/v2"
PAGES_ROUTE = ROUTE + "/pages"


def descriptor_response(record):
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("schema_version") != "v5.m18.v2.descriptor.v1":
        raise ValueError("M18_DESCRIPTOR_NOT_READY")
    return payload


def page_response(reader, page_number):
    if type(page_number) is not int or page_number < 0:
        raise ValueError("M18_PAGE_INVALID")
    return reader.page(page_number)


def build_routes(reader, descriptor):
    descriptor_response({"payload": descriptor})
    return {ROUTE: lambda: descriptor, PAGES_ROUTE: lambda page: page_response(reader, page)}
