# Phase 5F-2A: targeted Next.js security remediation

Verification date: 2026-10-18. Scope: dependency remediation only. This does
not supersede the outstanding acceptance findings in `PHASE_5F_VERIFICATION.md`.

## Dependency change

| Package | Before (manifest, lock and installation) | After |
| --- | --- | --- |
| next | 16.2.9 | 16.4.2 |
| eslint-config-next | 16.2.9 | 16.4.2 |
| react / react-dom | 19.2.4 | 19.2.4 (unchanged) |

Node 24.19.0 / npm 11.17.0 were used on Windows. Registry metadata for
Next 16.4.2 requires Node >=20.9.0 and accepts React ^19.0.0; its matching
ESLint configuration accepts ESLint >=9 and TypeScript >=3.3.1. Existing
versions meet these constraints. The installed Next upgrading guide was read.
16.4.2 was selected rather than the minimum 16.3.6 because the baseline audit
also reports Next advisories affecting versions before 16.3.8.

Only these tracked files changed in this phase:

- `frontend/package.json`: pins Next and its matching ESLint configuration.
- `frontend/package-lock.json`: reproducible resolved versions/integrities for
  those framework dependency trees, including Next env/SWC, SWC helpers,
  Sharp 0.34.5 -> 0.35.5 and its platform binaries/libvips, PostCSS -> 8.5.23,
  nanoid -> 3.3.20, and transitive runtime/queue/semver resolutions. The obsolete
  nested Next PostCSS entry is removed. No unrelated direct dependencies change.
- This verification report: advisory applicability, commands, results and limits.

Pre-existing uncommitted Phase 1-5 files are not attributed to this change.
Next-generated isolated-build additions to `tsconfig.json` were restored to
the pre-phase file. No application source, route, flag, backend, persistence,
algorithm, schema or teammate-owned workflow was changed. No audit-fix command
or codemod was run. `npm ls next eslint-config-next react react-dom --depth=0`
confirms the installed versions above. Deployment should use `npm ci` with this
lockfile and rebuild/restart the application; a clean deployment installation
was not performed here.

## Advisory verification and exposure

| Advisory | Precise published affected ranges | Patched versions | Applicability of pre-update repository |
| --- | --- | --- | --- |
| [GHSA-p293-qw3h-jr36](https://github.com/advisories/GHSA-p293-qw3h-jr36) | >=13.4.0 <15.5.24; >=16.0.0 <16.3.3 | 15.5.24; 16.3.3 | App Router, Windows host, no Cache Components configured: locally relevant conditions. Actual network exploitability was not tested. |
| [GHSA-vcvr-r3jv-pc5j](https://github.com/advisories/GHSA-vcvr-r3jv-pc5j) | >=16.2.0 <16.3.6 | 16.3.6 | Version affected; no next/og or ImageResponse use found in application source. The documented exploit requires Node ImageResponse rendering attacker-controlled SVG content/attributes/styles; Edge implementation is excluded by advisory. |
| [GHSA-2xp9-vwfh-vxw4](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4) | >=10.0.0 <15.5.24; >=16.0.0 <16.3.3 | 15.5.24; 16.3.3 | next/image is used for the public logo. Protected garment images use blob-backed img rendering. Advisory concerns AVIF optimization through Sharp/libheif; no AVIF exploit path is established by the tests. |

16.4.2 is outside all three affected ranges. Production OS, network exposure,
image sources and runtime configuration have not been inspected. A Windows
development host does not establish identical production exposure. The source
scan used `rg 'next/og|ImageResponse|next/image|cacheComponents' frontend/app
frontend/components frontend/next.config.ts`.

## Audit comparison

Counts are npm's vulnerable-package totals, not counts of independent exploits.

| Audit scope | Before | After |
| --- | --- | --- |
| Full dependency tree | 14: 1 critical, 12 high, 1 moderate | 10: 0 critical, 9 high, 1 moderate |
| `--omit=dev` | 6: 1 critical, 4 high, 1 moderate | 2: 0 critical, 1 high, 1 moderate |

The Next, Sharp, PostCSS and nanoid package findings disappear. No new vulnerable
package names appear. Existing findings remain:

- Production tree: `source-map-js` 1.2.1, high
  ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q));
  `baseline-browser-mapping` 2.10.36, moderate
  ([GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv)).
- Additional development-tree high entries: `brace-expansion`, `braces`,
  `browserslist`, `js-yaml`, and propagated findings through `micromatch`,
  `fast-glob`, `@next/eslint-plugin-next` and `eslint-config-next`.

These remaining findings need separate remediation review. In particular,
blindly accepting npm's suggested ESLint-config downgrade is inappropriate for
this matching Next 16 toolchain. Production dependency classification does not
prove a vulnerable function is remotely reachable. No clean security audit is
claimed. An initial post-update production audit request failed at the registry
endpoint; the repeated full/production audits both returned valid reports and
exit 1 for the remaining vulnerabilities. npm also reported an unapproved
`unrs-resolver@1.12.2` install script; no broad script approval was granted and
the functional checks below validate the installed environment only.

Raw before/after audit JSON, pre-phase package/lock/tsconfig copies and test logs
are retained locally in ignored `storage/verification/phase5f2a/`.

## Reproduction and verification

From `frontend`:

```powershell
npm audit --json
npm audit --omit=dev --json
npm view next@16.4.2 version engines peerDependencies --json
npm view eslint-config-next@16.4.2 version peerDependencies --json
npm install --save-exact next@16.4.2
npm install --save-dev --save-exact eslint-config-next@16.4.2
npm ls next eslint-config-next react react-dom --depth=0
npx tsc --noEmit
$env:SMART_WARDROBE_BUILD_DIR='.next-verification'
npm run build
Remove-Item Env:SMART_WARDROBE_BUILD_DIR
npm run test:browser
npm run lint
npx tsc --noEmit
```

Audit commands run before and after installation. The build variable was set
only in its build process; Playwright uses its own documented isolated
`.next-browser-verification` directory and temporary backend database. The
production build used the previously absent `.next-verification` directory.
No directory deletion was needed. Lint ran after browser completion to avoid
the previously observed test-results deletion race.

- TypeScript: initial and final checks pass, exit 0.
- Production build: passes, exit 0, Next 16.4.2, 13/13 static pages generated
  plus dynamic `/history/[chat_id]`; compilation reported 72 seconds. This
  build duration is not a recommendation response-time measurement.
- Playwright: **17 passed (1.9m)**, exit 0. Existing suite covers Homepage,
  Assistant, controlled failures, disabled Assistant without legacy fallback,
  retry/idempotency, historical read-only views, outerwear, save API reuse,
  session expiry/sign-out, completed history pagination/search and a real
  backend login-to-recommendation-to-history flow with cross-user 404.
- ESLint: exit 0, zero errors and two warnings from the updated
  `@next/next/no-location-assign-relative-destination` rule in
  `frontend/app/extract/results/page.tsx:151` and
  `frontend/components/Layout.tsx:50`. Existing internal navigation calls are
  flagged; no runtime failure was observed and no source refactor was made.

From `backend`:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

**639 passed, 1 failed, 1 warning in 81.55s.** The failure remains
`tests/test_report_architecture.py:28`,
`ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`,
asserting that the pre-existing `ai-services` directory must not exist. No
folders or assertions were changed. The warning concerns Starlette/httpx
TestClient deprecation. Geometry/CV tests were explicitly excluded because
their heavy CV dependencies are outside this frontend security phase.

This suite includes Phase 1-4, persistence, Homepage, Assistant, completed chat
history, wardrobe, authentication/cross-user and enabled/disabled capability
regressions. Backend flag tests retain explicit integrated-mode rejection when
disabled and legacy unqualified endpoint compatibility. No recommendation or
scoring policy changed. Approximate hexadecimal evidence remains disabled;
suitability remains opt-in.

From repository root: `git diff --check` passes, exit 0.

## Closure assessment

**PASS WITH LIMITATIONS; Phase 5F-2A is ready for review/closure.** The three
targeted advisories are removed from the dependency audit and no functional
compatibility regression was observed in the executed checks. No exploit
simulation, production deployment, clean-machine install, heavy CV test or
new performance measurement was performed. Production must install the lockfile
and rebuild/restart before this patch benefits its running instance.

Full FYP acceptance remains unapproved. Remaining audit findings, the existing
architecture assertion, review payload 422 followed by confirmation 409,
strict recommendation-source save/visualisation discrepancies, quality gates
and previously measured performance limitations remain separate work. No
Phase 5F-2B, teammate workflow fix or performance optimisation was started.
