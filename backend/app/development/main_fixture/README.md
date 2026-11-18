# Main synthetic fixture mode (Phase 2N-D)

Development-only, explicit fixture-only recommendation scope for the existing account. Normal B0/B1 acquisition and the original wardrobe are unchanged. TEST-2ND labels and authored fixture provenance are never owner review or model extraction.

Use the existing main frontend http://localhost:3000 and backend http://127.0.0.1:8000. Sign in normally, choose **My wardrobe**, open Outfit Assistant, and check **Synthetic test wardrobe only** for each new synthetic request. The original garments are excluded only in this explicitly selected scope. Leave the box unchecked for normal recommendations.

The declared wardrobe contains 30 images/garments. The existing male wearer admits 26; skirts/dresses remain denied. P1/C1, bounded non-contextual grammar 1.9 hard/soft requests only. Extra typed controls, P2/C2, contexts, save-as-outfit, VTON and continuation are unavailable for this new proof namespace. Normal functionality keeps its existing contracts. Changing a pinned row, image, wearer or saved P1 preference fails closed for new fixture selections; old history retains its captured facts. Material/fit are declared test metadata, not photographic conclusions.

## Local activation already applied

`SMART_WARDROBE_DEVELOPMENT_FIXTURE_PROFILE=phase2nd_main_fixture_v1`

This is disabled when the explicit profile is unset or when retired. The existing main environment remains production for its unrelated security/configuration rules; that setting neither activates fixture mode nor overrides this explicit development opt-in. Only the exact private database/account/catalog scope can use it. The private storage/phase2nd/runtime.private.json binds the exact database, catalog, owner/wearer and image hashes. It contains a proof secret: keep it private with the database backup. Do not commit that directory. Bounded compositional input uses its separate explicit profile; normal historical readers remain available.

## Safe later retirement

From the main **backend** directory using its existing Python environment:

```powershell
.\.venv\Scripts\python.exe -B -m app.development.main_fixture.manage retire
```

Review the dry-run list against storage/phase2nd/catalog.json. To apply exactly that policy:

```powershell
.\.venv\Scripts\python.exe -B -m app.development.main_fixture.manage retire --apply
```

Only exact registered fixture IDs with unchanged rows are considered. Later edited rows are skipped. Any captured fixture history causes unchanged fixtures to be archived and all history/media retained. Unreferenced unchanged fixture rows may be removed; media is always retained conservatively. The fixture capability is retired, while the proof reader remains. No prefix deletion, original garment deletion, account deletion or historical rewrite occurs. Do not restore the whole pre-population database after later user activity: that would discard the later activity. This is retirement, not an automatic deletion of private files.
