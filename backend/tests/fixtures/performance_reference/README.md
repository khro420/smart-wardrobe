# Frozen Phase 5F-2D-2A correctness reference

Captured on 2026-10-18 **before** production optimisations. `app.zip` contains
155 Python/JSON application and configuration files; `manifest.json` records
their SHA256 hashes. No environment files, databases, model assets or user data
are included. The archive is test-only and never loaded by the live application.

The subprocess worker verifies hashes and extracts the complete reference into
a disposable directory before importing it. Thus the original scorer does not
accidentally call optimised lower-level modules. Individual optimisation arms
use the live app with the other original scorer/ranker classes loaded from the
reference. The compatibility exception is explicitly aligned in these mixed
arms to avoid treating an otherwise identical exception as a different class.

The integrity test allows only the three approved live optimisation modules to
differ. Other source/configuration changes require explicit review of the
baseline's validity, rather than silently refreshing the oracle. Preserve this
reference when evaluating later optimisation phases.
