# Daily selection scope: new offline candidate, NOT production

Source and synthetic tests copied unchanged. This is a NEW candidate identity algorithm, NOT recovery of the historical generation algorithm. It preserves supplied group membership and does not recalculate selection formulas. Mapping from selected groups to intraday scope remains UNKNOWN. No real selections, monitor lists, freeze artifacts, calendar, bindings, private paths, credentials or unified controller are included.

Run `python -B -m unittest test_generator` and `python -B -O -m unittest test_generator`: 10 synthetic tests. Generated dates, rows and injected synthetic verifier are test fixtures, not real freeze/source/calendar admission. Default production_verifier refuses. Injected callbacks do not establish production authority.

approved_for_capture and production_allowed remain False. Original contract, resource/source gates, locks and current scope mapping are unbound. No capture, production registration, persistent write, network, natural-trigger or business acceptance. Separately blocked controller export is excluded.
