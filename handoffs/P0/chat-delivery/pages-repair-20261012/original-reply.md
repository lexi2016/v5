基于你提供的固定源码正文生成。基线为：

- `V5/src/v5_shadow/module_api.py`
- blob `d9d3f5f2ac06cb7802fade58829d00d6ca93c091`
- Reader 合同来自同一固定源码附件。fileciteturn68file0L5-L8

目标只解决：

```text
GET /api/v4/manager/m18/v2/pages
        ↓
module_api handler
        ↓
已保存 descriptor identity
        ↓
M18 v2 Reader.content/detail
        ↓
bounded JSON response
```

不改：

- descriptor route
- publication
- CAS
- manager/owner
- v2 generation
- 16MiB budget

以下为单文件 unified diff：

```diff
--- a/V5/src/v5_shadow/module_api.py
+++ b/V5/src/v5_shadow/module_api.py
@@ -20,6 +20,7 @@
 from .contracts import exact_keys,aware,sha
 from .digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
 from .api_gateway import (_parse_response, _precheck_json, _bounded_json,
                           _manager_response, MANAGER_WORKSPACE_PATH)
+from .m18_offline_v2_http_bridge import ROUTE as M18_ROUTE
 
 
 def response_key(module_id,path,query):
     return sha256_json(dict(module_id=module_id,path=path,query=query))
+
+
+def _m18_page_query(query):
+    if 'page' not in query:
+        raise ValueError('M18_PAGE_REQUIRED')
+    try:
+        page = int(query['page'])
+    except (TypeError, ValueError):
+        raise ValueError('M18_PAGE_INVALID') from None
+    if page < 0:
+        raise ValueError('M18_PAGE_INVALID')
+    return page
+
+
+def _m18_identity_from_descriptor(payload):
+    if not isinstance(payload, dict):
+        raise ValueError('M18_DESCRIPTOR_NOT_READY')
+    required = (
+        'schema_version',
+        'identity',
+        'run_id',
+        'generation_id',
+        'profile_sha256',
+        'status',
+    )
+    exact_keys(payload, required)
+    if payload['schema_version'] != 'v5.m18.v2.descriptor.v1':
+        raise ValueError('M18_DESCRIPTOR_NOT_READY')
+    if payload['status'] != 'READY':
+        raise ValueError('M18_DESCRIPTOR_NOT_READY')
+    if payload['identity'].get('run_id') != payload['run_id']:
+        raise ValueError('M18_IDENTITY_MISMATCH')
+    return payload
+
+
+def _m18_read_page_binding(config, root, query):
+    """
+    Read-only resolver for already published M18 descriptor.
+
+    It intentionally does not publish, rebuild bundles, refresh manager state,
+    or execute owners.
+    """
+    descriptor_query = {'run_id': query['run_id']}
+    descriptor, _ = read_response(
+        config,
+        root,
+        M18_ROUTE,
+        descriptor_query,
+    )
+    return _m18_identity_from_descriptor(descriptor['payload'])
+
+
+def _m18_page_response(config, root, query):
+    descriptor = _m18_read_page_binding(config, root, query)
+    page = _m18_page_query(query)
+
+    from .m18_offline_v2 import Reader
+
+    binding = config.get('m18_v2_binding')
+    if not isinstance(binding, dict):
+        raise ValueError('M18_READER_NOT_READY')
+
+    exact_keys(
+        binding,
+        (
+            'manifest_sha256',
+            'identity',
+            'profile_sha256',
+            'bundle',
+        ),
+    )
+
+    if binding['identity'] != descriptor['identity']:
+        raise ValueError('M18_IDENTITY_MISMATCH')
+    if binding['profile_sha256'] != descriptor['profile_sha256']:
+        raise ValueError('M18_PROFILE_MISMATCH')
+
+    reader = Reader(
+        binding['bundle'],
+        binding['manifest_sha256'],
+        binding['identity'],
+        expected_profile=binding['profile_sha256'],
+    )
+
+    value = reader.content(page)
+
+    return {
+        'schema_version': 'v5.m18.v2.page_response.v1',
+        'identity': descriptor['identity'],
+        'run_id': descriptor['run_id'],
+        'generation_id': descriptor['generation_id'],
+        'profile_sha256': descriptor['profile_sha256'],
+        'page': page,
+        'content': value,
+    }
```

然后替换 `do_GET()` 中：

```python
if parsed.path not in config['routes']:
    return self.error(404,'MODULE_ROUTE_NOT_CONFIGURED')

try:
    record,digest=read_response(config,root,parsed.path,query)
    self.reply(record['status_code'],record['payload'],digest)
```

替换为：

```diff
@@
             if parsed.path=='/__v5/module-health':
                 return self.reply(200,dict(status='READ_ONLY_RESPONSE_SERVICE',module_id=config['module_id'],release_id=config['release_id'],pid=os.getpid(),
                     implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=sha256_json(config),source_provenance_verified=False))
             if parsed.path not in config['routes']:return self.error(404,'MODULE_ROUTE_NOT_CONFIGURED')
             try:
-                record,digest=read_response(config,root,parsed.path,query);self.reply(record['status_code'],record['payload'],digest)
+                if parsed.path == M18_ROUTE + '/pages':
+                    payload = _m18_page_response(config,root,query)
+                    self.reply(200,payload,sha256_json(payload))
+                else:
+                    record,digest=read_response(config,root,parsed.path,query)
+                    self.reply(record['status_code'],record['payload'],digest)
             except FileNotFoundError:self.error(503,'MODULE_RESULT_NOT_AVAILABLE')
             except ValueError as error:
                 self.error(503,'MODULE_BUSY') if str(error)=='MODULE_PUBLICATION_BUSY' else self.error(409,'MODULE_RESULT_INVALID')
             except (TypeError,KeyError,OSError,RecursionError):self.error(409,'MODULE_RESULT_INVALID')
```

同时配置增加静态绑定：

```diff
--- a/V5/examples/m18_v2_module_api_config.json
+++ b/V5/examples/m18_v2_module_api_config.json
@@
 {
   "schema_version": "v5.module_api.v1",
   "module_id": "manager",
   "release_id": "m18-v2-readonly",
   "data_root": "<published module root>",
+  "m18_v2_binding": {
+    "manifest_sha256": "<existing v2 manifest sha256>",
+    "identity": {
+      "run_id": "46596b03c2ab4e29b1219fd2e5eb698f"
+    },
+    "profile_sha256": "<existing v2 profile sha256>",
+    "bundle": "<existing loaded Bundle object>"
+  },
   "routes": [
     "/api/v4/manager/m18/v2",
     "/api/v4/manager/m18/v2/pages"
   ]
 }
```

测试增加：

```diff
--- a/V5/tests/test_m18_v2_module_api_binding.py
+++ b/V5/tests/test_m18_v2_module_api_binding.py
@@
+def test_pages_route_requires_bound_reader():
+    config = make_config_without_m18_binding()
+    server = create_module_server(config)
+    response = get(
+        server,
+        "/api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0"
+    )
+    assert response.status == 409
+
+
+def test_pages_route_reads_existing_reader_page_only():
+    config = make_existing_publication_config()
+    server = create_module_server(config)
+    response = get(
+        server,
+        "/api/v4/manager/m18/v2/pages?run_id=46596b03c2ab4e29b1219fd2e5eb698f&page=0"
+    )
+    assert response.status == 200
+    assert response.json()['run_id'] == '46596b03c2ab4e29b1219fd2e5eb698f'
```

说明：

- 该 patch 不修改 publication。
- descriptor 仍由已有 `read_response()` 提供。
- pages 不再进入 `module_response` 查找，因此不会触发原来的 `MODULE_RESULT_NOT_AVAILABLE`。
- Reader 仍负责：
  - manifest SHA
  - identity
  - generation
  - profile
  - bounded content/page 校验。fileciteturn68file0L488-L578

测试执行状态：`NOT_RUN`。