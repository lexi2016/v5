# P0 integration overlay only

Base source: lexi2016/v4@6daed6271313b5ae5324c8948f163258ab8d1fa3, V5 subtree5a568d3d8bd653cc33c1ab35750871910c3e700d. Local baseline commit f39b4fc12ef057257d3c0eb3acedae618231251a; ledger increment2dc6cdbc1a7d67450e49ac40dec722c54dc33bf1; publication incrementb8b524edc8922d87a7c8f5b426709d42ae619bb1.

This is not a whole source transfer or runnable v5/main replacement. Obtain the exact authorized baseline V5 tree separately, apply integration.patch at its parent root using git apply --check first, and copy the included new integration_tests into that root. Use existing compatible Python/pytest. Historical saved-product integration test requires the original local M07 ledger/product evidence; it must report unavailable if absent, never fabricate a success fixture. Tests distinguish synthetic empty-owner plans from actual saved installation products. Local paths in logs are redacted; original evidence remains on Mac.

Only four product-file deltas, newly written integration tests/probe, fixed schedule source identities and sanitized receipts/logs are included. No original M13/M18 refused payloads, market data, existing large source tree, credentials, private runtime configs, screenshots or natural-success claims. No remote production activation. Full P1/business remains BLOCKED.
