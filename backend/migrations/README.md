# PostgreSQL + pgvector migration assets

`001_initial_schema.sql` is the deployment schema corresponding to Figure 4.14 and Tables 4.4-4.5 of the report. Apply it to PostgreSQL with the `vector` extension enabled before deploying the application server.

The local test configuration uses SQLite through the same persistence boundary so the repository remains runnable without an external database. SQLite runtime files are generated in private, Git-ignored `storage/` and are never deployment artefacts.
