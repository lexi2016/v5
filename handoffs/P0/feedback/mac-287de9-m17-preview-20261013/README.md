# Fixed M17 preview Mac acceptance

Candidate: `287de959ac160f6ae2792ca1f9684b4c86750012`.

New HTTP 9/9, Node 17/17, Vue component DOM 10/10, typecheck and build passed using existing matching dependencies. Initial eight loopback-bind EPERM errors were retried separately; the already passing test and old adapter suite were not rerun.

One preview deployment completed on 54780 with isolated source API 64303. Original 08c101 source API 62906, old dist/config, M18 backend and protected ports were retained. Module health release_id remains the existing saved source-bundle record identity; fixed deployment is verified by source Git blobs, implementation SHA256, and every served dist file hash.

Two isolated real M17 HTTP reads exactly matched prior accepted semantic response except fresh reader PID. No owner/claim/finish/collector/probe/network calls in instrumented reader path. Deployed real HTTP plus Vue/jsdom confirmed 100 rows, identities, safety flags, refresh/rejection clearing and M06/M08/M09/M10 results. M18 same-run three-strategy navigation passed. 137 protected files retained SHA256 and mtime.

Chrome control initialization and tab acquisition timed out. No Chrome visual acceptance or screenshot is claimed. DOM evidence uses real Vue components and real deployed HTTP, not a browser screenshot. No real payloads or filled bindings are included. Overall 18-module/P0-P5 acceptance remains incomplete.
