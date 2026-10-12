P0 targeted typecheck continuation

Parent: 07d0561faac2cf4a3d90e78bd87653fe94642a15 (preserves 291d92 integration and Mac feedback).
Only product change: frontend/tsconfig.json adds node to compilerOptions.types. @types/node is already in package.json and package-lock.json. The explicit types list previously included only vitest/globals, excluding the Node ambient declarations needed by already-included offline .spec.ts and fixture files. No new dependency, install, runtime Node import, browser polyfill, source exclusion, any cast or typecheck bypass.

Cloud: all 140 frontend blobs copied only after matching the parent Git blob. Static config/dependency/lockfile checks PASS. npm run typecheck --prefix frontend was attempted and exited 127: vue-tsc is not installed in available cloud dependencies. The cloud does NOT claim typecheck/build success. Original d53e and 07d frontend package.json/tsconfig.json bytes were identical; an earlier successful production build is not evidence that this full src-plus-tests typecheck command passed.

Mac: use the existing authorized Node environment and existing d53e node_modules. From this fixed candidate checkout, first run:
  npm run typecheck --prefix frontend
Only if exit 0:
  npm run build --prefix frontend
Then continue the already-authorized 291d92 source/API/UI preview acceptance. Do not repeat the already-passed 13 source, 11 API or 40 Node tests for this declaration-only change. Do not install dependencies unless actually absent and authorized. Retain the previous preview until the new build and readback pass.
