# Registered delivery outbox and internal unit reconciliation source

This incremental archive contains unchanged reviewed source and synthetic tests only. Registries remain empty. No real destination, account, credential, receipt, data, private binding, active lock or internal instruction is included. No actual message is sent, live job retried, or production state changed by preparing/testing this archive.

## Outbox
The local SQLite outbox keeps business identity stable across implementation revisions, records attempts and refuses blind retry after an uncertain attempt. Connector acceptance is not delivery. Stored state is checked against journal/receipt shape; even prior verified delivery requires fresh trusted verification. Channel, destination and payload identity must match.

This source has no real network connector or trusted delivery-verifier implementation. Those callbacks in tests return synthetic values. Actual authorization, destination, original owner locks/resource gates and normalized connector proof still require independent binding. Empty REGISTRY blocks use; adding a caller boolean is not production authority. No claim is made that a message reached a real recipient.

## Unit reconciliation
The classifier has no IO, source acquisition, process, lock, release or retry capability. It reports verified terminal success, known whole-attempt zero execution or UNKNOWN. Missing evidence, partial work, boolean fake counts, overlapping unknown attempts and conflicting success are not treated as safe zero execution. All action flags remain false. The production dispatcher is closed.

Its verify callback is a precondition, not an authentication mechanism. An actual original-owner caller must establish immutable references, exact full attempt/unit scope and original successful terminals under the original source/resource/lock rules. There is no such production binding in this package. Classifying an item does not grant permission to reuse, retry or release it.

## Verification and rollback
In `delivery`: `PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_outbox`, then repeat with `python -O`: ten synthetic tests. In `reconciliation`: corresponding `test_reconcile`, eight synthetic tests. Tests use temporary databases and mock callbacks, not live delivery or real stock reconciliation. No natural-trigger/business acceptance is established.

PROVENANCE and MANIFEST record source bytes and the allowlist. Revert this incremental commit if needed; prior files, main, V4 and production data remain unchanged. No previous module is replaced or granted authority by this upload.
