# Phase 5F-2E-3J-9: 150-garment capacity feasibility verification

2026-10-23, Asia/Kuala_Lumpur. **Verification complete; recommendation: 150 NOT YET DEMONSTRATED.**
All 48 submissions were correct, HTTP201, with distinct recommendation/chat IDs,
but **7/48 exceeded five seconds**. Balanced 150 passed these frozen cases;
outerwear-heavy 150 did not support the intended three-component suitability
configuration within the unchanged deadline. J-9 is ready for owner review as a
completed feasibility study, not approval of a 150-garment product maximum.
**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.**

## Frozen populations and actual counts

`backend/tests/fixtures/capacity_150.v1.json` freezes every row, J-7 source-row ID,
seed20261023, exact requests/preferences, attribute histograms, expected counts,
controls and the eight-cell schedule before performance collection. SHA256:
`dff276484d6d51faaeda360d814bba0d2523b63cba0578e5baf1cfb3486f5d95`.
`frozen-manifest.json` pins policies/vocabulary, expected exact identities and
collector/server hashes. No inputs were revised after seeing timed results.

| Population | Tops / bottoms / dresses / outerwear | Actual pair / trio / dress / dress+outerwear counts | Total |
|---|---|---|---:|
| Balanced150 | 60 / 60 / 15 / 15 | 3,600 / 54,000 / 15 / 225 | 57,840 |
| Heavy150 | 50 / 50 / 0 / 50 | 2,500 / 125,000 / 0 / 0 | 127,500 |

These counts were obtained by actual `RecommendationEngine` enumeration over
strict current owner/confirmed/available query snapshots, not just a formula.
Balanced categories:15 each short/long-sleeve top, vest, sling;20 each shorts,
trousers, skirt;4 short/4 long/4 vest/3 sling dresses;8 short/7 long outwear.
Heavy categories:13/13/12/12 tops,17/17/16 bottoms,25 each outwear category.
The existing category spellings and all four supported structures are unchanged.

Evidence uses J-7's labelled synthetic stratification, selected/cycled by category
with the fixed seed. It is **not an empirical population distribution** or human
fashion validation. Balanced colours:106 names,19 exact anchors,16 non-anchor hex,
9 missing; styles:91 single,37 multiple,9 missing,13 empty. Heavy colours:102 names,
22 anchors,22 non-anchor hex,4 missing; styles:97 single,25 multiple,16 missing,
12 empty. Missing/non-anchor evidence retains its actual unknown semantics.
Ordinary tags/patterns remain in the rows. No approximate hex matching is enabled.

Off request:`Suggest an outfit`. On request:`Suggest a casual outfit for campus.`
Every garment, including outerwear, has explicit synthetic owner Allow for campus
and casual formality. The real eight-occasion/two-formality evaluator, independent
mandatory verification and all-member conditions remain active. No missing
declaration is assumed allowed. Both profiles use the same immutable rows and
three equal-importance1 preferences:blue colour, vintage style, top group.

## Complete transport results

One direct HTTP call followed by five fresh browser calls per cell,48 total.
All first calls are included. Every cell completely enumerated and scored all its
structural candidates:57,840 or127,500 mandatory-valid/scored per call; **4,448,160**
candidates across the48 calls. No truncation, pruning or invalid fallback occurs.

| Population | Profile | Suitability | HTTP seconds | Browser seconds, all five in order | Browser median | Maximum | >5s / 6 |
|---|---|---|---:|---|---:|---:|---:|
| Balanced | Deferred | Off | 1.165958 | 1.355667, 1.213229, 1.299742, 1.398229, 1.338704 | 1.338704 | 1.398229 | 0 |
| Balanced | Experimental | Off | 2.119255 | 2.312295, 2.190409, 2.242729, 2.269068, 2.221714 | 2.242729 | 2.312295 | 0 |
| Balanced | Deferred | On | 1.851487 | 1.902082, 1.964493, 1.987599, 1.982002, 2.009756 | 1.982002 | 2.009756 | 0 |
| Balanced | Experimental | On | 2.809353 | 2.845571, 2.927672, 2.943777, 3.076685, 2.819257 | 2.927672 | 3.076685 | 0 |
| Heavy | Deferred | Off | 2.429639 | 2.634475, 2.756160, 2.616355, 2.472056, 2.570520 | 2.616355 | 2.756160 | 0 |
| Heavy | Experimental | Off | 4.120079 | 4.442135, 4.878884, 4.855537, 4.978791, 4.970138 | 4.878884 | 4.978791 | 0 |
| Heavy | Deferred | On | 4.388297 | 5.556433, 4.453614, 4.551506, 4.131372, 4.239742 | 4.453614 | 5.556433 | 1 |
| Heavy | Experimental | On | 5.675732 | 6.013035, 5.813074, 5.735804, 5.970441, 5.748855 | 5.813074 | 6.013035 | 6 |

All seven above-five-second results are retained:heavy deferred suitability first
browser5.556433s; heavy experimental suitability HTTP5.675732s and browsers
6.013035,5.813074,5.735804,5.970441,5.748855s. There were **zero HTTP/semantic errors,
timeouts or unsettled jobs**. A passing collector (1passed,6.2m) means evidence
collection/correctness succeeded, not that latency passed. Even heavy experimental
generic's4.978791s maximum leaves only0.021209s observed margin.

Full-precision HTTP/browser/backend/service/process-CPU times, resource snapshots,
cache ledgers, submission keys and complete exact identities are in
`performance-initial.json`; `timings.md` lists every service/CPU value alongside
all HTTP/browser trials. `summary-initial.json` is derived without filtering.

## Cache and identity correctness

The following ledgers repeat exactly across every call, with identical values for
generic and suitability within a workload/profile. Certificate evictions are
misses minus final size for this initially empty, uncleared session-local LRU.

| Population | Profile | Certificate hits | Misses | Evictions | Pair hits / misses / evictions |
|---|---|---:|---:|---:|---|
| Balanced | Deferred | 57,763 | 77 | 0 | 0 / 0 / 0 |
| Balanced | Experimental | 51,437 | 6,403 | 6,147 | 160,200 / 5,625 / 0 |
| Heavy | Deferred | 127,432 | 68 | 0 | 0 / 0 / 0 |
| Heavy | Experimental | 121,537 | 5,963 | 5,707 | 370,000 / 7,500 / 0 |

The certificate/aggregation capacities remain256 and the pair capacity19,900.
Experimental final pair sizes are5,625 balanced and7,500 heavy; no pair evictions.
Every candidate still receives mandatory/independent checks before any numeric
certificate reuse; hits do not represent skipped candidate enumeration. No cache
bound or scoring policy changed.

All48 full score/provenance fingerprints match the corresponding frozen offline
expectation. Full exact Fraction components, raw Unknown/NotApplicable evidence,
decision bounds/basis, preference snapshot, policy hashes and execution provenance
remain stored. Prefixes below are for scanning; full hashes/identities are in
`expected-results.json` and every trial. IDs expand as `balanced-150-NNNN` or
`outerwear-heavy-150-NNNN`, ordered upper/lower/optional outerwear here.

| Population | Profile | Suitability | Selected IDs in role/order sequence | Exact total | Fingerprint prefix |
|---|---|---|---|---:|---|
| Balanced | Deferred | Off | 0003, 0062, 0144 | 3/10 | `03eea1fbd81e15a6` |
| Balanced | Experimental | Off | 0003, 0105 | 2/5 | `5bdf431115944975` |
| Balanced | Deferred | On | 0003, 0062, 0144 | 1/1 | `0e900bcb3b4e5eda` |
| Balanced | Experimental | On | 0003, 0105 | 1/1 | `c01da906da6a7046` |
| Heavy | Deferred | Off | 0001, 0053, 0127 | 3/10 | `e5d75979fdd56dbc` |
| Heavy | Experimental | Off | 0001, 0057, 0134 | 11/30 | `ac25d22d64db4098` |
| Heavy | Deferred | On | 0001, 0053, 0127 | 1/1 | `2354208dc37167ff` |
| Heavy | Experimental | On | 0001, 0057, 0134 | 29/30 | `580c05ed73e0d7b0` |

Different profiles may legitimately choose different winners. Heavy experimental
uses a PartiallyConventional decision5/6 with raw Unknown (empty outerwear style);
this is the unchanged disclosed midpoint policy, not fabricated measured quality.
The offline public-oracle tests cover all candidates in reduced populations;
these are arithmetic/functional checks, not independent fashion ratings.
Persisted counts are24 recommendations and24 completed chats per owner; all48 keys,
recommendation IDs and chat IDs are distinct. Focused tests separately verify
atomic rollback, immutable history, replay, ownership and eligibility changes.

## Resource qualification and measurement boundary

Before collection, two retained resource checks found CPU46/47/68% and71/48/48%,
about5.3GiB free RAM; Roblox consumed about19% machine CPU in each separate delta
window. **Zero timed submissions** occurred then. After owner workload reduction,
CPU18/19/14%,RAM7.9GiB were observed. No user applications were closed by the agent.

The automated gate retained8 preflight samples (CPU5-56%,RAM7.35-7.40GiB), then
passed with three consecutive **5/19/11%** observations. The unchanged controls are
CPU<=20%,free RAM>=4GiB,10s settle,120s bounded wait. There was one automated
collector run, no timed replacements/retries; both earlier blocked manual checks
are retained separately. All96 before/after timing snapshots show CPU4-76%,
RAM6.45-7.47GiB. These are **preflight-qualified sequential observations, not
continuous isolation**. Backend/browser activity and residual background activity
can affect them; no specific process is proven to explain any individual delay.
The failures are not discarded as environment-only. Post-run CPU9/5/6% and raw
process deltas (including OneDrive activity) are retained separately.

One Uvicorn0.54.0 process and production Next16.4.2 use the existing3201/3200
loopback/proxy setup, real login/JWT, disposable SQLite and a retained J-6 build
`Q3jwGpqXBc9FUVrN9gGr8`. All27 recorded frontend app/component/lib/package/config
inputs match J-6; no build was needed. Existing240s collector waits and proxy
timeouts are unchanged. No tests/builds/profilers overlapped timing collection.
Each request gets fresh session-local caches; the separate offline expectation
process cannot warm the transport process's recommendation caches.

Browser T0 is submit click, T1 the visible correct complete recommendation
component, matching J-8. Login/page preparation are outside timing. Protected
synthetic thumbnails are available, but completed image loading is not part of
T1. Real-image/network/GPU/deployment performance is not certified. Service and
process CPU observations include actual exhaustive ranking and atomic persistence.
No inference, migration or production database is used.

## Comparison with retained 200-garment evidence

Balanced150 has42.90% of balanced200's134,820 candidates; heavy150 has94.57%, only
5.43% fewer and2.20times balanced150. Heavy150's experimental generic median4.879s
approaches J-7 balanced200's4.776s and J-8 corrected generic4.744s. Heavy150's
experimental suitability median/max5.813/6.013s remain above5s despite fewer
garments. J-8's balanced200 corrected suitability median/max6.629/7.350s and
HTTP8.988s, J-7's9.865s browser/9.169s HTTP and all their slow/failed/blocked trials
remain unchanged. No causal cross-phase speedup is claimed:population/evidence,
composition, request mix and resource conditions differ.

J-7/J-8 balanced200 certificate hits/misses:deferred134,735/85; experimental
123,340/11,480 (11,224 evictions), with380,800 pair hits/10,000 misses/no pair
evictions. Compare the J-9 ledgers above; cache behaviour depends on exact evidence
keys as well as candidate count. It is not proof of representative reuse rates.

Within J-9, suitability-request median increases over generic are0.643s/0.685s
(balanced deferred/experimental),1.837s/0.934s (heavy). Experimental-over-deferred
median increments are0.904s/0.946s (balanced off/on),2.263s/1.359s (heavy).
These sequential differences include the changed request fields, mandatory
checks, R/P weights and existing scoring pipeline; they are not isolated causal
estimates of compatibility arithmetic or suitability toggling alone.

## Verification, source integrity and scope

- New fixture/public-oracle tests:10passed,6.71s; focused combined regressions:
  **569passed,110.37s**, including default/rollback, all8/2 suitability values,
  Deny/Unknown/malformed/conflict, independent checks, exact arithmetic, bounded
  caches, owner isolation, persistence/replay and historical actions.
- Four-way reference/compact x deferred/experimental production browser functional
  suite:**28passed,46.2s**, seven structures/evidence scenarios per combination.
- TypeScript and scoped collector/config ESLint:exit0. No broad backend suite
  rerun; no new defect justified one. The known ai-services assertion and separate
  CV/torch/model/deployment acceptance remain outside this focused run.
- Initial offline setup assertion inspected a factory name rather than its
  produced evaluator type; corrected helper and retained initial failure log.
  No production change or weakened policy followed it.
- Final frozen-input/build/source checks and `git diff --check` are recorded in
  `integrity.json` and `diff-check-final.log`. Earlier phase evidence is preserved.

Only new verification files are added:the capacity fixture, disposable server,
focused backend test, Playwright collector/config, this report, and the phase's
raw artifacts/helpers. Existing production/upload/confirmation/frontend source,
schemas, algorithms, feature defaults and historical records are unchanged.
TypeScript regenerated its ignored build-info cache; that is not source logic.
The file inventory/hashes and exact commands are in the phase evidence directory.

Current defaults remain **compact_exhaustive / compatibility_deferred / suitability
disabled**. Experimental scoring remains explicitly selected only in disposable
verification, with exact60/20/20 weights. J-6's full-score certificate optimisation
and accepted J-8 facts SHA256
`cb98ff0f62e51724789acb5cb812bdcf0b7bcf0bd66ee420ceda68f466a2a4f3` remain present.
Four structures, exact eligibility, complete streams, deterministic ranking,
unknown evidence, immutable history and reference rollback are unchanged.

## Capacity decision and remaining acceptance

**150 NOT YET DEMONSTRATED.** Do not adopt150 as a generally supported maximum on
this evidence. Balanced150 is promising for these bounded cases, but heavy150
exceeds5s in all six intended experimental-suitability observations; even its
generic experimental maximum has negligible measured margin. A total limit alone
cannot guarantee performance across arbitrary category/evidence distributions.
Do not add category quotas or automatically substitute100 garments.

**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** The original5s target is unchanged;
this is a bounded feasibility study, not approval of hardware, workload, statistic,
final scoring release, real images, concurrency, database or deployment baseline.
Five browser repetitions and one HTTP call per cell cannot establish a universal
bound. Prior200-garment failures are not retroactively passed.

No total per-user garment quota is currently enforced;100 IDs remains a per-request
review/confirmation restriction. If a maximum is later approved, separate owner/
teammate work must define count semantics (including archives), transaction-bound
whole-batch/concurrent-confirm rejection, consistent backend/frontend feedback,
atomic rollback and race tests. Testing150 does not enforce it. Further engineering,
capacity/product-policy decisions, default activation or formal NFR collection
need their own approval. **No later phase begins; wait for owner review.**
