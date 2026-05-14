# scripts/

Operational scripts for the BiteFit nutrition app.

## `init_supabase_schema.py`

Create the relational schema on the database pointed to by `DATABASE_URL`.

### When to run it

* **First-time Supabase setup**, after you've created the project and copied
  the connection string into `.env` or your deployment secrets.
* **Adding new tables.** The script uses `Base.metadata.create_all` and is
  idempotent — existing tables are left alone, missing ones are created.

### Configuration

The script reads `DATABASE_URL` from the environment. A `.env` file at the
repo root is loaded automatically when `python-dotenv` is installed.

| Environment | Example `DATABASE_URL` |
|---|---|
| Supabase Postgres | `postgresql+psycopg://postgres:PASSWORD@db.<project>.supabase.co:5432/postgres` |
| Local SQLite (fallback) | *(unset — defaults to `sqlite:///storage/nutrition.db`)* |

### Usage

```bash
# From the repo root
python scripts/init_supabase_schema.py
```

The script prints the resolved (credential-redacted) URL, the dialect, and
the list of tables it touched.

### What it does *not* do

* It does **not** apply Supabase Row Level Security (RLS) policies. RLS must
  be added in the Supabase SQL editor — see
  `storage_audit/data_layer_audit.md` for the recommended policies
  (`USING (user_id = auth.uid())`).
* It does **not** seed any data.
* It does **not** add a foreign key against `auth.users`. That table lives
  in the `auth` schema, separate from `public`, so a public-schema FK is not
  declared. Application code enforces the `user_id` contract.

### Related

* `nutrition_app/persistence/database.py` — engine / session factory and
  `DATABASE_URL` resolution.
* `nutrition_app/persistence/models.py` — the ORM models that define the
  schema.
* `storage_audit/data_layer_audit.md` — the authoritative multi-user
  contract this schema implements.
