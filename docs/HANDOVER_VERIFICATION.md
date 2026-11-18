# Windows handover verification — 18 November 2026

The documented CPU setup was executed from a clean source copy in a path with
spaces, with a newly created Python virtual environment, fresh pip installation,
`npm ci`, a separate database and newly generated credentials. Existing live
ports 3000/8000, database, images and environment files were left unchanged.

Verified environment: Windows, Python 3.12.10, Node 24.19.0, Next 16.4.6,
React 19.2.4. Setup and startup are in `scripts/Setup-Windows.ps1` and
`scripts/Start-Windows.ps1`. See the root README for commands and GPU requirements.

| Check | Result |
|---|---|
| Fresh CPU installation and backend/frontend readiness | Passed on separate loopback ports |
| Package integrity and independent historical proof reconstruction | All 32 transferred fixture/mixed proofs passed |
| Account initialization | New local password and signing material; no shared credentials |
| Existing-installation protection | Re-running the installer retained credentials/configuration |
| Wardrobe/media | 51 available records: 21 original + 30 synthetic; all 51 preferred image hashes matched authenticated HTTP responses |
| Real browser | Signed in using the UI; wardrobe images rendered in installed Edge |
| Authenticated recommendation HTTP | Jeans, shopping, inferred interview default and soft preference passed exact R/C/P/T checks, History and receipt replay |
| Continuation | Ten distinct bases through ordinals 0–9; final server-issued continuation action absent |
| Explicit preferences and feedback | Like, repeated Like, Dislike, Clear, and a saved-colour preference edit passed through the existing authenticated APIs |
| Diversity and transferred history | Two neutral requests selected different exact-score-tied outfits; a transferred recommendation reopened through its historical reader |
| Focused backend verification | 56 unique cases satisfied: original run 53 passed / 3 setup errors, corrected fixture isolation then 3 targeted passes |
| Focused frontend checks | Four explanation/personalization test files passed; TypeScript passed |
| Student 1 integration | Group geometry, mocked detection/pipeline, activity and optional attribute fallback tests passed |

The initial fixture setup errors were caused by the inherited development
configuration pointing at the clean installation rather than the test's own
disposable database. The fixture now explicitly binds its generated configuration;
the production foreign-database guard was preserved. An initial snapshot import
attempt exposed immutable triggers firing during restore. The installer now loads
rows before installing the exact triggers and verifies the completed database
before publication. An initial browser assertion used a nonexistent `main` element;
correcting the diagnostic selector required no application change.

Next was updated from 16.4.2 to 16.4.6, including its matching ESLint configuration,
after the old development server reported upstream security advisories. Compatible
transitive lockfile fixes were applied. `npm audit --omit=dev` reported zero
vulnerabilities at verification; 14 high development-tool dependency advisories
remain. No forced breaking dependency upgrade was applied.

## Limits

- The package contains 58 garments (seven archived), six saved outfits,
  124 recommendations and 70 chats, with 58 physical media files. There are 469
  pre-existing missing older media references, mainly processing/try-on history.
  All currently available preferred garment images are included.
- Fresh installation import MACs attest independently verified imported proofs;
  they do not claim possession of the original signing key. Historical contents
  and identities remain unchanged. Old continuation actions may refuse when their
  captured source/settings scope differs after transport; start a new chat.
- CPU development adapters are explicitly labelled substitutes. CUDA, Detectron2,
  TryOffDiff, CatVTON, embeddings and real GPU inference need hardware/model
  installation and verification on the destination PC.
- Strict historical-authority assertions remain unchanged. External missing
  historical evidence and prior NFR-02 failures are not recertified by this check.
- Source-machine secrets and password hashes are absent from the new package.
  Older published Git history is not rewritten; initialize new local credentials
  and do not reuse previously shared demo passwords or keys.

This is a functional handover, not a performance or model-accuracy certification.
