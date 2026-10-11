# 全部52份固定源码路径

所有路径相对于原出处仓库根。离线解压后位于 original/source/<path>；新独立仓库默认保留路径层级，实际迁移映射须显式记录。

原出处：lexi2016/v4@f7cb731c384ee6890a87d16c19a5b5a621779477

## 原producer内部静态闭包（12文件）

- `handoff/v4-running-source-20261005/canonical/ops/build_a_share_close_review.py`；SHA-256 `f3a465e3a79a32241971ce38d95c79767a211e41e40918989fbff8968b703f53`；8360 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/data_store.py`；SHA-256 `7cef1dba8fa2c917411220e123184950d2abc3b10dff8d608e70f8d52a61f2bd`；10704 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/trading_safety.py`；SHA-256 `ae5d63d2ad6974dc4863dff6c5f56335bafe485f9b0b172bf929346a853ba7df`；2597 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/market_time.py`；SHA-256 `e72e8eb1bef136859c5379fae2eab6d94c5612959b3a8ab8e75f101954a001f1`；960 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/interprocess_lock.py`；SHA-256 `9b0cb80a1fe1bcbdebb3936134c8f0bad258c9c9236356022551ff7753351df0`；7514 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/owned_io.py`；SHA-256 `9a74731287ca7c9667643557d4ae42f63453a025665ba28f5b65fdbff7d54ee0`；9354 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/a_share_review_store.py`；SHA-256 `ce22b5f217cf5c9ac0f71650ff88b3b17088580f79e9bac670be795ed8894482`；10176 bytes
- `handoff/v4-running-source-20261005/canonical/infrastructure/owned_path.py`；SHA-256 `c766e74a963818f32b0eadf964e262148ddb8d7f8b090a2ccbb5d83124164b30`；2251 bytes
- `handoff/v4-running-source-20261005/canonical/domains/a_share_review.py`；SHA-256 `90845aa31a4cac828a0be73ff40a65c06d6a016dcdf0e723602e855311afceeb`；7038 bytes
- `handoff/v4-running-source-20261005/canonical/domains/close_review_chain.py`；SHA-256 `207ed5f9c13531db66a54d0a3fd2f7502612aba3dcce8d5eb5a53f0291b4d63c`；10549 bytes
- `handoff/v4-running-source-20261005/canonical/contracts/a_share_review.py`；SHA-256 `2c6b845aea3186a416eb12ab297bd3c242cc6cc248961b47e32f43d1f1192fa6`；261 bytes
- `handoff/v4-running-source-20261005/canonical/domains/a_share_close_model.py`；SHA-256 `140d3aabb0f24a55d05d0c624e4563694af050fe2ac02910292fc026d7de7e4a`；12302 bytes

## 所有附入源码/配置

1. `V5/README.md`
   - SHA-256 `7abaade6654d84cd93c378a609f4db3e9b9dec45db338ac7407f782ec34eee57`；Git blob `4e44173cee5f43e034f9aef3710ba9a15873b225`；2487 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
2. `V5/contracts/a_close_source_manifest.json`
   - SHA-256 `1b433f3b88f97e21b6ff33d084b9fcdccde5b90a43a220eefbf7a6b8c5a55f27`；Git blob `71eac2236bd97c202cf887ce341911e603d4d241`；1214 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
3. `V5/pyproject.toml`
   - SHA-256 `0a1824d3b255ee7f8391919254b2c21bf0deaf6da11a1b8cfc3e3a58c6fd4584`；Git blob `94de0b747be243f6309da810fa3ce058e643b52a`；262 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
4. `V5/src/v5_shadow/__init__.py`
   - SHA-256 `c53107e04e471793978e7ea517445a937bf46fd8f3005452e34f683712c1774c`；Git blob `152582c71d7e49884749beb490e192ff4cb8ca6c`；83 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
5. `V5/src/v5_shadow/a_close_review.py`
   - SHA-256 `b288b916f43a41cfc7bd95511ad6decfd537a4cccf64ba5875f13dc04fad1933`；Git blob `8696f56b59475e73a4432a2b7f0874251ab89bed`；8008 bytes
   - 角色：MODULE_SCOPED_CANDIDATE_DIFF_ALLOWED_AFTER_BASELINE_CHECK
6. `V5/src/v5_shadow/a_preselection.py`
   - SHA-256 `e666660830b2f088c51ba00b9fafdefcf966efb798c25a5c21b18ba1c74aa74b`；Git blob `05dd0b28f14bd794890f514e130d8090a1b0438b`；29140 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
7. `V5/src/v5_shadow/api_gateway.py`
   - SHA-256 `9bdb76f8cbbdd020ba414f183fc8e8af9ad5306baf6ccc7f9458d45c660cc225`；Git blob `c5677fb59a4847a24f16a12d5412fce293168fc0`；16003 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
8. `V5/src/v5_shadow/composition.py`
   - SHA-256 `258462c4ee53a3ee7acc4f8e0e0f35b4b20994f9ec4dd6ee48f37a6a68c981b0`；Git blob `d22723df42b71537210aa621afb05dfab6be517f`；5297 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
9. `V5/src/v5_shadow/contracts.py`
   - SHA-256 `eee026873e0d765fcedf52077daea823edf6ee7013f37c106c82b66a4582d85a`；Git blob `5efda704a231165255c4f6ab240a25385e5cff54`；7256 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
10. `V5/src/v5_shadow/daily_close_plan.py`
   - SHA-256 `f51af9be40a32de88ea55672fffb7b7c74570c9d1ae6053b488b51a4d89bf3f6`；Git blob `b816802e512a8f22d736716168c515f5ade61ca0`；5807 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
11. `V5/src/v5_shadow/daily_dispatch.py`
   - SHA-256 `a7d0a9bfe672fd670ee3c7504a0b25c1a0365498c0520b71d16e38bc93cae240`；Git blob `f5d45abea6a159f01756decb23049b825cd0f906`；3438 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
12. `V5/src/v5_shadow/digests.py`
   - SHA-256 `134b1a13b7ff677afef6f556e2a750d94cc54a396cbdcff111c5d67e645280e5`；Git blob `e6bc1557cd96cee5b35cb20ed4f45d8a61a74925`；425 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
13. `V5/src/v5_shadow/module_api.py`
   - SHA-256 `8ce7e4ce59a724629cdc25e407e1b66f2d2aed79e7ae6779b6c3145de020b6ca`；Git blob `3fdea5f256b2dc70df141a0e70dbbc1396abb859`；15282 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
14. `V5/src/v5_shadow/module_artifacts.py`
   - SHA-256 `07c1ab119367abbdb73363ca4f4d0af2d05e3bbef5e02be911a77a6a31f02e17`；Git blob `acf2195fee3711f594982269f1e6ab81da40a905`；7936 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
15. `V5/src/v5_shadow/provider_evidence.py`
   - SHA-256 `e1dc88fa0095ebd17c274290340b562f8a03ef41bf8bfadf713d4a58452948e5`；Git blob `5d72d3b2d54c0449576e46e7eba7be4fbc7884d6`；6446 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
16. `V5/src/v5_shadow/run_ledger.py`
   - SHA-256 `2258adcf6f1f61640e9ee2bb36cae5daa06670293f4227fc431289c858077dfd`；Git blob `1187e3b7633682d61985984afdf0699508cefd59`；6105 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
17. `V5/tests/test_a_close_review.py`
   - SHA-256 `fe331baa493299720380d6e8332947aa635b0e52d3b24a2b291bfdd20ca8c1f8`；Git blob `7d02a794ad918fb1cb19f1198281d8b7ee83ad3d`；3759 bytes
   - 角色：MODULE_SCOPED_CANDIDATE_DIFF_ALLOWED_AFTER_BASELINE_CHECK
18. `V5/tests/test_daily_close_plan.py`
   - SHA-256 `23f0ff9eb5938d96eb46611064d1b74861f14194507c6a7b859562ef67cc9f6e`；Git blob `4ad9d199b9dcf0020755ae53c2aecbb83b62baff`；4958 bytes
   - 角色：READ_ONLY_SHARED_INTERFACE_OR_REFERENCE
19. `V5/vendor/a_close_baseline/contracts/market_calendar_2026.json`
   - SHA-256 `9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb`；Git blob `c8177cfdeb55c038a88e915f206780eeba8b0d32`；3473 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
20. `V5/vendor/a_close_baseline/contracts/trading_calendar.py`
   - SHA-256 `584f28d18273a8824c5f68a701aa4404123b5c71900caada3e2772828991ee8f`；Git blob `dc18a1ac447242a15a0e543606aa8076ca452fbc`；9291 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
21. `V5/vendor/a_close_baseline/domains/a_share_close_model.py`
   - SHA-256 `140d3aabb0f24a55d05d0c624e4563694af050fe2ac02910292fc026d7de7e4a`；Git blob `96e914f73117d162f1ad7c1e4538ce07c23c1afb`；12302 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
22. `V5/vendor/daily_schedule_baseline/contracts/market_calendar_2026.json`
   - SHA-256 `9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb`；Git blob `c8177cfdeb55c038a88e915f206780eeba8b0d32`；3473 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
23. `V5/vendor/daily_schedule_baseline/contracts/runtime_workloads.json`
   - SHA-256 `7389cae30de08cf68c31e5b0bb6f5b17fead403366946496b7a4de148229d0ef`；Git blob `abdcae3adfcd56b4c33b2752e14c8fffb844f351`；51682 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
24. `V5/vendor/daily_schedule_baseline/contracts/trading_calendar.py`
   - SHA-256 `584f28d18273a8824c5f68a701aa4404123b5c71900caada3e2772828991ee8f`；Git blob `dc18a1ac447242a15a0e543606aa8076ca452fbc`；9291 bytes
   - 角色：READ_ONLY_FROZEN_SOURCE_OR_CONTRACT
25. `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/_review_router_parts/http_routes.py`
   - SHA-256 `5d0f487f7396dcefdeb4e3fdb72926327714276ce0e5f0aff26788ec91eedde6`；Git blob `f884abb7215902e8e42b8d598458a14ca49dfbc9`；8579 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
26. `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/_review_router_parts/stage_partial.py`
   - SHA-256 `776be68ef0c44478d347527417fbbff873143ba7f206ba14d967fad9059d358f`；Git blob `ad0b161ea8b7452a318797bdb56eaba13038087e`；3940 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
27. `handoff/v4-running-source-20261005/canonical/apps/api/v35_api/_review_router_parts/stage_rows.py`
   - SHA-256 `54946d92b28bd8f5a6a6a004d92356b74e18efad245e309f03c67fae12b8baa3`；Git blob `ede71d8edb71d03603ab72a81ceda6d5503ea453`；9465 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
28. `handoff/v4-running-source-20261005/canonical/contracts/__init__.py`
   - SHA-256 `6334176641872990a56b559f965a9dc6d65f29ab0a0efc0752ef1a73fe42bc7d`；Git blob `bdeb74d7a882d62b6f3eb78a06b8127f2121ff40`；55 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
29. `handoff/v4-running-source-20261005/canonical/contracts/a_share_review.py`
   - SHA-256 `2c6b845aea3186a416eb12ab297bd3c242cc6cc248961b47e32f43d1f1192fa6`；Git blob `af2110155081887e723f329652f7f73feb88d273`；261 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
30. `handoff/v4-running-source-20261005/canonical/contracts/market_calendar_2026.json`
   - SHA-256 `9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb`；Git blob `c8177cfdeb55c038a88e915f206780eeba8b0d32`；3473 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
31. `handoff/v4-running-source-20261005/canonical/contracts/stages.py`
   - SHA-256 `d0ac1771a1005888e53e9a322da65f959cfbcbcc665357b8783d5eb4eda9c6df`；Git blob `41bf1ba5de290c23a22695d9454b4991976c3e39`；2036 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
32. `handoff/v4-running-source-20261005/canonical/contracts/trading_calendar.py`
   - SHA-256 `eca22a1e45271df45fc0a3b7cec28cec4e448d1af97b80371cc5c3c1953ec0f1`；Git blob `b0a6a32d8b2e14c7bb054a1ded35d93da1bc504c`；10239 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
33. `handoff/v4-running-source-20261005/canonical/domains/a_share_close_model.py`
   - SHA-256 `140d3aabb0f24a55d05d0c624e4563694af050fe2ac02910292fc026d7de7e4a`；Git blob `96e914f73117d162f1ad7c1e4538ce07c23c1afb`；12302 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
34. `handoff/v4-running-source-20261005/canonical/domains/a_share_review.py`
   - SHA-256 `90845aa31a4cac828a0be73ff40a65c06d6a016dcdf0e723602e855311afceeb`；Git blob `09a6d078ab4bcf17d5e22c91e9750fbcf116411c`；7038 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
35. `handoff/v4-running-source-20261005/canonical/domains/close_review_chain.py`
   - SHA-256 `207ed5f9c13531db66a54d0a3fd2f7502612aba3dcce8d5eb5a53f0291b4d63c`；Git blob `1adee020ca74c4efa5323f76b9bcfd7259e8a966`；10549 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
36. `handoff/v4-running-source-20261005/canonical/domains/review_envelope.py`
   - SHA-256 `f18cc6f9e8242447ad404255e89918f5a6a399073e13699ffb415235cd33314e`；Git blob `221f0917aeceab608fe1d484b225df39fb46d5e7`；4067 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
37. `handoff/v4-running-source-20261005/canonical/infrastructure/__init__.py`
   - SHA-256 `46068d69d6783fdcd33b3428ae3c7e8e690d5149f4f00837f6b1d1184dd6f47b`；Git blob `647f68415f88ab9dfb514686554c9f9abf4c1cd6`；68 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
38. `handoff/v4-running-source-20261005/canonical/infrastructure/a_share_review_store.py`
   - SHA-256 `ce22b5f217cf5c9ac0f71650ff88b3b17088580f79e9bac670be795ed8894482`；Git blob `cbe9fd6e29ab0b1fea6025fc18bcc2854f79f415`；10176 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
39. `handoff/v4-running-source-20261005/canonical/infrastructure/data_store.py`
   - SHA-256 `7cef1dba8fa2c917411220e123184950d2abc3b10dff8d608e70f8d52a61f2bd`；Git blob `c1cc44f6d6e70a363cf5722b145a805ff73e1e4d`；10704 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
40. `handoff/v4-running-source-20261005/canonical/infrastructure/interprocess_lock.py`
   - SHA-256 `9b0cb80a1fe1bcbdebb3936134c8f0bad258c9c9236356022551ff7753351df0`；Git blob `a97e733725834235fbcc9129639ae198fa8770cd`；7514 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
41. `handoff/v4-running-source-20261005/canonical/infrastructure/market_time.py`
   - SHA-256 `e72e8eb1bef136859c5379fae2eab6d94c5612959b3a8ab8e75f101954a001f1`；Git blob `bcac1bd49b6861d60f8820e0bbc7dd7fa42c8fd0`；960 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
42. `handoff/v4-running-source-20261005/canonical/infrastructure/owned_io.py`
   - SHA-256 `9a74731287ca7c9667643557d4ae42f63453a025665ba28f5b65fdbff7d54ee0`；Git blob `1b6666551980c44ebb0b05f133c189909d79c7df`；9354 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
43. `handoff/v4-running-source-20261005/canonical/infrastructure/owned_path.py`
   - SHA-256 `c766e74a963818f32b0eadf964e262148ddb8d7f8b090a2ccbb5d83124164b30`；Git blob `2d9873a41c09a05c62975210a13a59bf350a1a5a`；2251 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
44. `handoff/v4-running-source-20261005/canonical/infrastructure/trading_safety.py`
   - SHA-256 `ae5d63d2ad6974dc4863dff6c5f56335bafe485f9b0b172bf929346a853ba7df`；Git blob `5f10cfb51cb3dacd327447475964e0f6867ee89f`；2597 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
45. `handoff/v4-running-source-20261005/canonical/ops/build_a_share_close_review.py`
   - SHA-256 `f3a465e3a79a32241971ce38d95c79767a211e41e40918989fbff8968b703f53`；Git blob `d8295efa1d082917522d93f3d9396ee154a0926f`；8360 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
46. `handoff/v4-running-source-20261005/canonical/ops/import_a_share_review_reference.py`
   - SHA-256 `13d4368d1677b158a3b6c7862d6b8d1b70a2e07895544699e92f610d93490524`；Git blob `7808c1d71ec4c0adb1b2fee79ce8882ef968d5c2`；2771 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
47. `handoff/v4-running-source-20261005/canonical/ops/run_v35_close_review_node.py`
   - SHA-256 `e48e27969d79a1e09f31bdd4be35fb3ade0822ee5e80e43888ceb1abe3bda856`；Git blob `6635895c84d53b81378889d99b27015aa0e38324`；17352 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
48. `handoff/v4-running-source-20261005/canonical/ops/run_v35_close_review_slot.py`
   - SHA-256 `08f46d928dc70fabf2c1ca49d96b5fa64dc67f113909ed3ce66b81bfcad67ae5`；Git blob `4535a1a6883cd9ea5aa1d60e1565f5b87f3fa585`；10143 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
49. `handoff/v4-running-source-20261005/canonical/tests/test_a_share_close_model.py`
   - SHA-256 `bc0629b73daeb8e7bc2c6c49864bd22ad197eeb6489b7f4c9c7bf5af0b44a38f`；Git blob `6cc2a43d7c0bc3982b5768ee98ac058546d8e68b`；4191 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
50. `handoff/v4-running-source-20261005/canonical/tests/test_a_share_review.py`
   - SHA-256 `b909b4219c39d9124300fcc612ccbfa28a39cdfa8d876277dd0c706536292d19`；Git blob `3fe2333f9a8441e95c16593e96b4644da12ec9e1`；16004 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
51. `handoff/v4-running-source-20261005/canonical/tests/test_a_share_review_store.py`
   - SHA-256 `e6ecafecd3c0552113cc11e284ff9903e9a4d6089e99d0ce0ca0b128299441e3`；Git blob `f97fabd893e1625983e27211e2bf28203c19c3f4`；9426 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
52. `handoff/v4-running-source-20261005/canonical/tests/test_close_review_chain.py`
   - SHA-256 `34b5ff1ada6e10df74ecb65d2ddf9b2bb5a8108da8887599c626231b5f8342f8`；Git blob `e28ee3f56f403f79d772b87c1f896aee8e022c98`；7344 bytes
   - 角色：READ_ONLY_HISTORICAL_DONOR
