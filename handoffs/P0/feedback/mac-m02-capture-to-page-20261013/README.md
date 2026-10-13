# M02 Mac capture to saved read-only page

Result: PASS_WITH_SOURCE_IDENTITY_ONLY_LIMITS.

Fixed candidates: capture 776acce9328aa102e3db6973405f01260f15239d; builder ce6cddce1ef52d63241f0d8192b6adcc118ea750; M02-only saved publication a451275c5eee5ec63139b7e8f886624ebdd4c7d5.

receipt.json contains the executed commands with relative paths and $PY/$NODE aliases, original UTC timestamps, exits, actual dual-plate responses, capture hashes, all seven membership hashes, builder/reader identity and publication CAS generations. $PY and $NODE denote existing approved runtimes; no dependencies were installed. JSON is an acceptance record, not an executable replay recipe. Do not replay its capture command or remove its retained claim.

The new binding uses target 20261013, signal 20261012, eligibility source 20261013, a real cutoff after membership availability, and require_pit=false. The existing builder and a separate process using its original reader returned identical saved results. Publication called only publish_m02_saved_binding with action=read and the exact predecessor generation. It retained M01/M03/M05 canonical rows and the other ten route identities; no generic source bundle recomputation, service restart or preview code switch occurred.

Direct API, preview proxy and DOM passed. DOM used the existing compiled frontend and real preview HTTP. Native visual was NOT_RUN. M06 remains target 20261014 / signal 20261013 / 100 rows; the manager run remains unchanged. Product sources, old binding, protected bytes and listener PIDs were checked unchanged.

SOURCE_IDENTITY_ONLY / CANNOT_CONFIRM and all safety/eligibility flags remain false. Membership prior-cutoff rejection remains HK_UNIVERSE_V2_AVAILABILITY_UNPROVEN_BY_AS_OF. This does not establish formal PIT, 20261014 membership, full M02 acceptance or whole-project acceptance. Capture panel_status remains PENDING_PANEL_GATE.

Only this README.md and receipt.json are intended for upload. Raw requests, source data, full saved binding, process logs and private paths remain local. Existing logs and bindings were preserved. This continuation did not repeat the earlier capture, recovery or offline tests.
