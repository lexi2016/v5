# Dependencies and source closure

Copied owner: fixed f7cb731c384ee6890a87d16c19a5b5a621779477; original handoff manifest 73 entries checked with zero SHA/size mismatch. Runtime donor selection is 54 unchanged files plus one explicitly new V5 build manifest: domains, infrastructure, contracts and ops. Exact origin map is the V5 `.sources.json` descriptor. Descriptor verification rejects changed/missing/extra source files and symlinks. Runtime does not use stale pycache.

Observed cloud interpreter: Python 3.12.14. Existing primary environment: pydantic 2.13.4, pandas 2.2.3. Existing pytest 9.1.1 was loaded from a pre-existing test environment for the test process only; owner subprocesses use isolated primary Python (`-I -B`). No packages were installed.

NOT_INSTALLED in primary cloud: requests, akshare, langgraph, langchain-openai, openai. Do not infer those are absent on Mac. Pure original intraday import uses pydantic through original prompts; requests is required later in HTTP acquisition, including certain fixture transport flows. Real daily graph needs original LangGraph/model dependencies and authorized real profile/config/source material. No fallback graph or fake provider is provided.

Historical F original manifest remains unrecovered. Recovered r4 original is retained but is incompatible with F assembly/Iwencai. The authorized reproducible V5 build manifest uses a new schema/build identity and wrapper-fixed external SHA; the unchanged original validator verifies all F 40+5 exact bytes. This supplies new build trust, not historical provenance.

Original tests additionally reference historical input/vibe_reference/duanxian/intraday.py with SHA 3c9c2bc3b6d97d545ba2eeca417b116e2456c4904606aed746324d6e2cc507c5, full router/scheduler closure and Mac-specific saved artifacts not supplied here. Preserve NOT_RUN rather than inventing them.
