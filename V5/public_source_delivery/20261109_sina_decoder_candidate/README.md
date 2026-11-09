# Sina KLC candidate wrapper (not production)

This directory contains project-authored wrapper code only. No vendor SDK or decoder implementation is redistributed. A separately obtained, lawfully usable local decoder with SHA256 `0effc9a3924b63f8c7f10c6ac4ed8b2654599ebc3ec762348bf96a42f056f48a` is required. Its identity derives from the `xh5_S_KLC_D` function in Sina's public SDK at https://finance.sina.com.cn/sinafinancesdk/js/sf_sdk.js, SDK SHA256 `804645b741da7969c3f4fb1a4f5f9608d50b312f8efb1a6523d389441eae40b6`. Vendor reuse/redistribution terms remain UNKNOWN; public availability is not an open-source license.

This candidate is NOT the historical decoder with SHA256 `39a599c94dde4df1c2eb0882d4bff9560160cfd52ead0797cebb04b3122c2f52`. Hash pinning does not constitute production admission. Original source, factor, basis, date, resource, lock and independent review gates remain required.

CLI: `node --max-old-space-size=96 adapter.cjs SYMBOL RAW DECODER NEW_OUTPUT`. The wrapper never fetches a decoder, evaluates a full SDK, or overwrites an existing output. Input collection must remain size-bounded before file reads. Node vm is not a security boundary for arbitrary malicious code; only the reviewed pinned dependency is accepted.

Offline validation covered three SZ stocks and malformed inputs. SH/BJ grammar support is not a claim of tested source coverage. Latest tested bar was 2026-11-06, not proof of later collection or natural scheduling success.

## Reproducible synthetic checks
Run `node test_synthetic.cjs` with Node built-ins only. These checks cover API shape, six rejected inputs before vendor execution, and exclusive output preservation. They do NOT execute the vendor decoder or prove market-data validity. Separate private fixture verification used three real SZ histories; those fixtures and vendor code are intentionally not distributed here.
