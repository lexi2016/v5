# M04 historical archive compatibility read

Fixed product: 8a3c1d2013e34b7e070fd924e1ee754f7dfd8de7. This is one read of existing 20261012 21:00 materials, source run hip-49cb26f7f3a0661bde1d1440; not new acquisition, builder/import acceptance, PIT verification or full M04 acceptance.

The older 69-file / 34-product binding does not include the target 20261012 archive or receipt. This run copied exactly the original manifest.json, research/archives/20261012.json and receipts/research/archives/20261012.json into a new private root. All three SHA256 values are in report.json. No manifest was trimmed or rewritten. The original source SHA/size/mtime and copied file hashes were checked before/after.

Actual entry: the fixed research_ingest_daily.cold_read(archive_binding) with archive_binding={root:<NEW_PRIVATE_ROOT>,files:<THE_THREE_EXACT_SHA_BINDINGS>}. It calls original archive_reader.read_private and launches exactly one independent interpreter; the exact redacted child argv, UTC times, exit and output hashes are in report.json. The parent validates the frozen source/request identities. No run/build/import/provider command was called. Existing Python 3.14.6 was used; no dependency install.

Target record records["20261012/"] has no error, contains 18 articles, and its complete payload equals the original archive JSON. The full original manifest references other uncopied products; 53 out-of-sample record errors remain explicit. They are not accepted records and were not repaired. This is a bounded single-record compatibility result.

All 18 articles lack retrieved_at and available_at. Batch fetched/collected_at and source publication available_at remain distinct; publication time is not substituted for article-level clocks. PIT remains UNKNOWN, natural_verified=false, historical_pit_claimed=false. No V3 acquisition receipt or historical clock was fabricated.

Raw reader output, business content, exact private binding and paths remain local. To reproduce only when separately needed, retain the three original bytes and call the fixed read command with that exact binding; never invoke run or discovery. Existing successful evidence should be reused instead of repeating this read.
