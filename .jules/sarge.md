## 2026-03-10 - Fix Vitest hanging in CI
**Bottleneck:** The frontend `npm test` step was hanging indefinitely in GitHub Actions because `vitest` runs in watch mode by default.
**Optimization:** Updated `.github/workflows/ci.yml` to run `npm test -- --run` instead of `npm test`, forcing vitest to run once and exit.
**Impact:** Resolved the hanging CI job, allowing the frontend tests to complete successfully and the pipeline to finish.
