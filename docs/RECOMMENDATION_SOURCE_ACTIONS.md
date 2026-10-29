# Phase 5F-2E Integration: confirmation and recommendation-source actions

Authority: explicit user/teammate approval for these integration corrections.
Original Project I FR-DW-09/11/16-19, FR-VIS-01-05/08, RN-11/23/28 and sections
4.6.4 and 4.8.2 require reviewed confirmed garments, current owned source
revalidation, separate Outfit creation and unchanged historical recommendations.
The exact strict Phase 1 processing-item/job-owner policy remains unchanged.

## Review and confirmation

Actual browser path: extract upload -> processing job API -> background processing
-> results GET -> ReviewItem API validation -> accepted review -> confirmation
transaction -> persisted confirmed garment -> ConfirmedGarmentQuery. The results
page previously sent neckline and sleeve_length inside attributes, even when null.
ReviewItem deliberately forbids these keys, so review returned 422 and a subsequent
confirmation correctly returned 409 because the item was not accepted.

The correction removes only these unsupported properties. Existing descriptive
neckline/sleeve custom tags remain. Existing valid custom tags are preserved and
deduplicated with descriptive tags. Unchanged list-valued fit/style/material
attributes retain their original values instead of being flattened to a display
string on acceptance; edited values use the existing permitted string/null
representation. Existing tag-count limits still apply, with no silent truncation.
Backend schema, review-before-confirmation, ownership and processing checks are
unchanged. Missing review cannot be bypassed. No CV/VTOFF algorithm is changed.

## Strict recommendation-source action boundary

recommendation_actions.strict_items reads the owned Recommendation and ALL ordered
items, rejects empty/duplicate/noncontiguous references, and obtains eligible
snapshots only from the injected transaction-bound ConfirmedGarmentQuery. It
compares every ID against that complete eligible set; no invalid item is dropped.
The new factory is wired by infrastructure composition, not imported as concrete
Digital Wardrobe persistence into Recommendation. Both original query operations,
including legacy ID behavior, remain unchanged.

Accepted/pending/rejected/NULL/dangling processing items, wrong processing-job
ownership, unavailable/archived/deleted/missing or foreign garments fail. The
helper does not rerun NLP, original request conditions, scoring or ranking; current
eligibility is distinct from matching the original historical request.

## Atomic save and independent saved indicator

Save uses BEGIN IMMEDIATE before strict validation and keeps the same SQLite
connection until Outfit/OutfitItems commit. The lock prevents a competing writer
from invalidating the checked garments before insertion. Any write failure rolls
back the whole operation, including BaseException inside the write body. No
Garment, Recommendation, RecommendationItem, metadata, display snapshot or chat
is changed. Garment roles and ordering are copied exactly.

A deterministic UUIDv5 over a versioned JSON tuple (user ID, Recommendation ID)
is the new Outfit ID. This gives one durable save target per user/recommendation
without a migration, new cross-entity foreign key or modified history. Concurrent
retries serialize and return the same existing outfit; first successful name wins.
Retries still revalidate the original source. Independently edited saved outfits
remain independently managed. Archived save targets are not silently recreated.
Creating/cloning a second outfit from the same recommendation is not a new feature.

Legacy status=saved records have no trustworthy original Outfit mapping. They
remain readable, are not repaired, and a new save is rejected with controlled 409
rather than guessing a matching outfit or creating another duplicate. Existing
legacy saved indicators remain supported.

GET /recommendations/{id}/saved-outfit authenticates the Recommendation owner and
returns independently derived current saved/outfit_id state. The frontend uses
this endpoint for new records and its existing local state after saving, retaining
legacy status support. A late false state response cannot undo local save success.
The recommendation status is not repurposed as mutable UI state. No historical
save/visualise controls are enabled by this phase.

## Visualisation preparation, creation and execution

Only recommendation sources gain the strict Phase 1 action check. Saved-Outfit
source predicates and VTON algorithms remain unchanged. Preparation uses a short
read transaction; request creation already uses BEGIN IMMEDIATE, now including
strict source validation before queued request/item insertion. Existing protected
media ownership/resolution and category-based VTON mode checks remain in place.
Recommendation roles reject unsupported outerwear/unknown roles; legacy garment/
accessory labels remain readable where the existing category-mode contract supports
them. Unsupported outerwear categories also fail even if mislabeled with another
role. Outerwear is never dropped from a layered recommendation to claim success.

Execution revalidates a queued recommendation when claiming it, before loading
media or invoking VTON. It compares current source IDs/media/category/roles/order
with the queued snapshot and rejects changes rather than swapping inputs. Failures
produce the existing failed-job outcome. The short transaction ends BEFORE media
loading and long inference. No transaction can guarantee garments remain unchanged
throughout inference without holding locks across inference; this implementation
guarantees current eligibility at request creation and execution claim. It does not
claim stronger perpetual freshness or alter generation behavior.

## Verification and remaining limits

Focused tests include actual upload/review/confirmation APIs with synthetic
detector/standardisation output, upper/lower categories, null/array fields,
unsupported keys, strict-query inclusion, independent SQLite connections, eight
concurrent saves, writer contention, injected item-insert failure, complete history
equality, corrupt duplicate references, invalid second members, cross-user access,
unsupported roles/categories, no job on invalid source, and queued-source changes
without inference. Browser tests use real APIs and an actual synthetic image
upload in development AI mode; they do not certify real model extraction quality.

The frozen performance archives/fingerprints are NOT regenerated. Historical
source-integrity tests now accept only the exact seven approved integration file
hashes in integration_actions_sources.v1.json (six changed files and one addition).
They retain their previous algorithm-change guards and archive hash validation.
All other completed-2D1 application files, including score arithmetic, generation,
mandatory evaluation, ranking and compatibility evidence, remain byte-identical.

SQLite transaction tests do not certify PostgreSQL deployment. A future PostgreSQL
adapter needs explicit transaction-bound validation and appropriate row locking/
isolation for both garment and processing records; BEGIN IMMEDIATE semantics cannot
be assumed to transfer. No schema migration is introduced in this stage.

Real GPU-backed CV/VTOFF/VTON validation remains separate. Style-clearing null/empty
semantics, technical suitability-tag UX/provenance, CV empty-pixel black ambiguity,
historical frontend actions, RN-17 activation and NFR-02 remain prior limitations.
Suitability stays opt-in; approximate hex matching and holistic compatibility stay
disabled. See PHASE_5F_INTEGRATION_VERIFICATION.md for commands/results/inventory.


## Historical frontend actions follow-up

Phase5F-2E-Integration-UI enables independent save/visualisation actions on completed
chat views. The earlier historical-frontend-actions limitation is superseded only
for this scope. See [HISTORICAL_RECOMMENDATION_ACTIONS.md](HISTORICAL_RECOMMENDATION_ACTIONS.md)
for behavior, requirement references, test commands and remaining limitations.
