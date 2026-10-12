# c68fa0 real binding configuration canary — blocked before HTTP

Fixed runtime candidate unchanged: **c68fa0a374355fb510a9d0e3fa595da09296f033**.
No seven-test rerun. No product modifications or publication changes.

Generated LOCAL_ONLY_config.json from the author's V5/examples/m18_v2_module_api_config.json, filling existing verified manifest_sha256, all six identity fields, profile_sha256 and bundle_root from the saved local preview-binding-plan. data_root uses the retained 912941 publication; release_id uses its real receipt value mac-912941-canary. Both advertised routes retained. No invented keys, in-memory Bundle adaptation, rebuild or republish.

Actual command:
```text
<EXISTING_PYTHON> <TASK>/bound_canary_c68fa0.py
```
UTC 2026-10-12T08:00:42.808403–08:00:42.857566; exit **1**.

Actual original API call:
```python
create_module_server(config, host="127.0.0.1", port=0)
```

Failure:
```text
module_api.py:276 create_module_server → _config(value)
module_api.py:148:
    exact_keys(value,('schema_version','module_id','release_id','data_root','routes'))
contracts.py:130:
    raise ValueError('CONTRACT_FIELDS_INVALID')
ValueError: CONTRACT_FIELDS_INVALID
```

The filled example's m18_v2_binding is rejected by the runtime top-level configuration contract. Server was **not created**, no port bound, no GET sent. Therefore descriptor/pages six-identity HTTP results for this bound attempt are **NOT_REACHED**.

This differs from previous feedback 9e9c78ac45e900c14b3174818c6b04b8bfeaf96f: that original canary omitted m18_v2_binding and reached pages HTTP409. This attempt actually supplies the author-provided binding keys and real saved values, then fails before HTTP.

Existing publication file SHA256 map unchanged before/after. Real bundle was not rebuilt or reverified; existing identity/manifest pin evidence reused. Private paths/config stay local. V4/old services untouched; no owner, acquisition, trading or browser.

Required author contract resolution: accept/parse the advertised m18_v2_binding through the original configuration entry point and specify a consistent usable saved-bundle binding. No field was removed or runtime patched locally to bypass this rejection.
