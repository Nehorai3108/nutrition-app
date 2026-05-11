# Parallel Agent Plan — Multi-User Auth + Data Isolation

**Goal**: Activate Supabase auth and add per-user data isolation so a friend can sign up and only see their own inventory, meal plans, workouts, etc. Demo-ready outcome.

**Strategy**: 4 phases. Phase 1 has 3 agents in parallel. Phase 2 has 3 agents in parallel. Phase 3 and 4 are sequential. Use git branches per agent so they don't fight over the same files.

---

## Wall-clock estimate (if parallelism is fully used)

- Phase 0 (you, manual): 20 min
- Phase 1 (3x parallel Sonnet): ~30 min
- Phase 2 (3x parallel, 2x Opus + 1x Sonnet): ~90 min
- Phase 3 (1x Opus, sequential): ~30 min
- Phase 4 (1x Sonnet, sequential): ~20 min

**Total: ~3 hours** vs ~8 hours sequential.

---

## Model recommendations summary

| Phase | Agent | Model | Why |
|---|---|---|---|
| 1A | Data Layer Audit | **Sonnet 4.6** | Read-heavy, produces report |
| 1B | Auth Integration Audit | **Sonnet 4.6** | Read-heavy, produces report |
| 1C | Storage_Agents Audit | **Sonnet 4.6** | Read-heavy, produces report |
| 2A | Auth Integration | **Opus 4.7** | Threads new concept through 2600-line app, edge cases |
| 2B | Data Layer Refactor | **Opus 4.7** | Schema design + migration + every repository touched |
| 2C | Storage_Agents Refactor | **Sonnet 4.6** | Mostly mechanical path changes |
| 3 | Integration & Merge | **Opus 4.7** | Merge conflicts, validation, end-to-end thinking |
| 4 | Verification | **Sonnet 4.6** | Click-through testing, no deep reasoning |

---

## PHASE 0 — Manual setup (you, ~20 min)

Before any agent runs:

1. Go to [supabase.com](https://supabase.com), create a free project (any region; closer = faster).
2. From the Supabase dashboard, copy these four values:
   - **Settings → API → Project URL** → `SUPABASE_URL`
   - **Settings → API → anon public key** → `SUPABASE_ANON_KEY`
   - **Settings → API → service_role key** → `SUPABASE_SERVICE_KEY` (keep this secret!)
   - **Settings → Database → Connection string → URI (Direct connection)** → `DATABASE_URL`
3. Add them to your `.env` file:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_ANON_KEY=eyJhbGc...
   SUPABASE_SERVICE_KEY=eyJhbGc...
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
4. Verify `.env` is listed in `.gitignore`. If not, add it.
5. In Supabase: **Authentication → Providers → Email** → make sure it's enabled. **Disable email confirmation** for demo speed (Auth → Settings → "Confirm email" off).
6. Create branch baseline:
   ```
   git checkout main
   git pull
   git checkout -b feat/multi-user-foundation
   git push -u origin feat/multi-user-foundation
   ```

---

## PHASE 1 — Discovery (3 parallel sessions)

Run all three at the same time in three separate terminal windows. Each writes a markdown report to `storage_audit/`. None modify code.

### 1A — Data Layer Audit (Sonnet 4.6)

```
You are auditing a Streamlit nutrition app to plan a multi-user refactor. Read-only — DO NOT modify any code.

Goal: produce a contract that other agents will implement. List every database entity and classify each as user-scoped (private to one user, e.g., inventory) vs shared (catalog data, e.g., USDA food list).

Read these locations:
- nutrition_app/repositories/*.py (every public method)
- nutrition_app/models/ and any SQLAlchemy model files (grep for "Base" / "Mapped" / "Column")
- The schema of storage/nutrition.db (use: sqlite3 storage/nutrition.db ".schema")
- nutrition_app/persistence/ or wherever the engine is configured

Produce one file: storage_audit/data_layer_audit.md

Required sections:
1. **Tables inventory** — table name, columns, current PK, classification (user-scoped / shared / system), reasoning
2. **Repository methods inventory** — file:method, current signature, reads/writes which tables, classification
3. **THE CONTRACT** (most important — other agents will follow this verbatim):
   - Exact list of methods that must accept `user_id: str` as their first parameter
   - Exact list of tables that must add a `user_id: str` column (Postgres UUID, indexed, NOT NULL)
   - Exact list of tables that DO NOT change (shared)
   - Default user_id value for local dev fallback (suggest: "demo")
4. **Migration notes** — anything tricky about backfilling existing rows (the demo can wipe data; just call this out)

Be exhaustive but concise — every method and table must be listed exactly once. Use tables, not prose.
```

### 1B — Auth Integration Audit (Sonnet 4.6)

```
You are auditing a Streamlit nutrition app to plan adding Supabase login. Read-only — DO NOT modify any code.

Goal: identify every place "current user" is implicitly assumed today, so the next agent can wire st.session_state["user_id"] cleanly.

Read these locations:
- app_user.py (the main 2600-line Streamlit app)
- ui/ folder (Streamlit components)
- chatbot/ (Groq client — does it already track a user?)
- start_bitefit.py and main.py (entry points)

Tasks:
1. grep for "st.session_state" across the entire codebase. List every key currently in use.
2. Find the page navigation logic in app_user.py — where does the sidebar / option_menu live? This is roughly where the login gate goes.
3. Find every CALL SITE of repository methods (e.g., "InventoryRepository(", "user_repo.", etc.) — list as file:line. The next agent must pass user_id at every one.
4. Identify the existing "Profile" page flow — does it create a UserProfile? How does it know "who" the user is today?
5. Identify any places hardcoded user IDs / "default user" / similar exist.

Produce one file: storage_audit/auth_integration_audit.md

Required sections:
1. **Login gate placement** — exact file, approximate line, suggested structure (st.stop() pattern is fine)
2. **session_state keys today** — table: key, where set, where read
3. **Repository call sites** — table: file, line, method called, suggested user_id source
4. **Existing profile flow** — how it works now, what changes
5. **Hardcoded user references** — anywhere "default", "demo", or similar appears

Be exhaustive on call sites — missing one means broken queries after the refactor.
```

### 1C — Storage_Agents Audit (Sonnet 4.6)

```
You are auditing a Streamlit nutrition app to plan multi-user data isolation. The storage_agents/ folder contains JSON files written by a multi-agent system. Read-only — DO NOT modify any code.

Goal: classify each storage_agents/ file/folder as per-user (a specific user's meal plan) vs global (system-wide audit log) and recommend a new path structure.

Read these locations:
- ls -R storage_agents/ (full tree)
- Open 2–3 example JSON files from each subfolder to understand the schema
- grep "storage_agents" across the Python codebase to find every read/write site
- nutrition_app/agents/agent_7_data/ (data manager — likely owns most of this)
- nutrition_app/agents/agent_8_director/, agent_9_critic/ (write to audit/)

Produce one file: storage_audit/storage_agents_audit.md

Required sections:
1. **Folder tree** — every subfolder + what's in it
2. **Per-folder classification** — table: folder, content type, per-user / global / hybrid, reasoning
3. **Read/write sites in code** — file:line, what it does, what changes
4. **Recommended new structure** — concrete paths, e.g.:
   - `storage_agents/users/{user_id}/plans/...` (per-user)
   - `storage_agents/system/audit/...` (global)
5. **Migration plan** — script outline to move existing files (assume current single user = "demo")

Director and Critic logs are likely global (system observability). Meal plans are per-user. Be explicit about each.
```

---

## PHASE 2 — Implementation (3 parallel sessions)

Wait for all three Phase 1 reports to exist. Then run these three in parallel on separate branches.

### 2A — Auth Integration (Opus 4.7)

```
You are implementing Supabase auth in a Streamlit nutrition app. Branch: feat/auth-integration. Branch from feat/multi-user-foundation.

CRITICAL READING (do this first, in order):
1. CLAUDE.md (project conventions)
2. storage_audit/auth_integration_audit.md (your roadmap)
3. storage_audit/data_layer_audit.md — specifically THE CONTRACT section. You must match it.

Goal: Add Supabase authentication, gate the app behind login, and propagate user_id everywhere. DO NOT touch repository implementation logic — another agent (feat/data-layer-multi-user) is doing that in parallel. Stay in your lane.

Tasks:
1. Create auth/supabase_client.py:
   - Loads SUPABASE_URL and SUPABASE_ANON_KEY from .env
   - Exports get_supabase() -> Client
   - Exports get_current_user() that returns the user from session_state, or None

2. Create auth/login_ui.py with a Streamlit login/signup component:
   - Email + password
   - Sign Up and Log In tabs
   - On success: st.session_state["user_id"] = response.user.id; st.session_state["user_email"] = response.user.email; st.rerun()
   - Handle errors gracefully (wrong password, duplicate email)

3. Modify app_user.py:
   - At the top (after imports, before any page logic): if "user_id" not in st.session_state: render login_ui and st.stop()
   - Add a logout button in the sidebar that clears session_state and st.rerun()
   - Remove any hardcoded "default user" assumptions identified in the audit

4. At every repository call site listed in storage_audit/auth_integration_audit.md, pass user_id=st.session_state["user_id"] as the first argument.

5. In repository class definitions: add user_id: str as the first parameter to every method that the contract identifies as user-scoped. ONLY change signatures + add the parameter to method bodies as a passthrough placeholder. DO NOT change SQL/query logic — the data-layer agent will. Add # TODO(data-layer-agent): filter by user_id where logic must change.

6. Update the existing Profile page to NOT ask for "who you are" — the user_id from auth is the answer. Profile becomes "biometric data for current user."

7. Run pytest. Some repository tests will fail — note them in a comment in app_user.py with "# data-layer-agent will fix" but do not fix yourself. Auth tests should all pass.

8. Commit in logical chunks. Push the branch.

Constraints:
- DO NOT modify nutrition_app/repositories/ implementations (only signatures)
- DO NOT modify SQLAlchemy models
- DO NOT modify the database connection string
- DO NOT modify storage_agents/ paths (other agent is doing that)
- DO modify all repository CALL SITES in app_user.py and any UI components

Output: feat/auth-integration branch, all auth wiring complete, login screen works, repository signatures match the contract.
```

### 2B — Data Layer Refactor (Opus 4.7)

```
You are refactoring a Streamlit nutrition app's data layer for multi-user. Branch: feat/data-layer-multi-user. Branch from feat/multi-user-foundation.

CRITICAL READING (do this first, in order):
1. CLAUDE.md
2. storage_audit/data_layer_audit.md — your roadmap. THE CONTRACT section is binding.
3. storage_audit/auth_integration_audit.md — for context only (which call sites the other agent is updating)

Goal: Add user_id scoping to every user-scoped table and repository method. Migrate connection from SQLite → Supabase Postgres while keeping SQLite as a local-dev fallback. DO NOT touch app_user.py or UI — another agent (feat/auth-integration) owns that. Stay in your lane.

Tasks:
1. SQLAlchemy models — for every table in the contract marked user-scoped:
   - Add column: user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
   - Do NOT add a foreign key (Supabase auth.users lives in auth schema, separate from public)

2. Repository methods — for every method in the contract:
   - Add user_id: str as the first parameter
   - Add WHERE user_id = :user_id to every SELECT
   - Set the user_id on every INSERT
   - For UPDATE/DELETE: add user_id to the WHERE clause (defense against ID guessing)

3. Database connection — in nutrition_app/persistence/ (or wherever create_engine lives):
   - Read DATABASE_URL from .env first
   - If unset, fall back to sqlite:///storage/nutrition.db with a logged warning
   - Adjust connect_args / pool settings appropriate to Postgres vs SQLite (check_same_thread only applies to SQLite)

4. Schema initialization for Postgres:
   - Add a script: scripts/init_supabase_schema.py
   - Connects via DATABASE_URL, runs Base.metadata.create_all()
   - Run it once to create tables in Supabase. Document this in scripts/README.md.

5. Tests — every test fixture that creates a repository must now pass user_id="test_user_1" (or similar). Update conftest.py if it exists. All repository tests must pass against SQLite (Postgres is for prod).

6. agents/food_cache.db (separate USDA cache) — leave alone, it's a global cache, not user data.

7. Commit in logical chunks. Push the branch.

Constraints:
- DO NOT modify app_user.py (the auth agent is editing it in parallel)
- DO NOT modify ui/*.py
- DO NOT touch storage_agents/ folder paths
- DO modify nutrition_app/repositories/, nutrition_app/models/, nutrition_app/persistence/, tests/
- The user_id column is a string (UUID format from Supabase), not an integer

Output: feat/data-layer-multi-user branch, schema migrated, repositories filter by user_id, pytest green.
```

### 2C — Storage_Agents Refactor (Sonnet 4.6)

```
You are refactoring file paths in a Streamlit nutrition app's agent storage. Branch: feat/storage-agents-namespacing. Branch from feat/multi-user-foundation.

CRITICAL READING:
1. storage_audit/storage_agents_audit.md — your roadmap

Goal: Make per-user agent storage paths actually per-user. Keep global system paths global.

Tasks:
1. Create nutrition_app/storage_paths.py with helper functions matching the audit's recommendations. Examples:
   - user_plans_dir(user_id) -> Path
   - user_tasks_dir(user_id) -> Path
   - system_audit_dir() -> Path
   - system_director_log() -> Path
   Each helper ensures the directory exists (mkdir parents=True exist_ok=True).

2. For every Python file that references storage_agents/ (per the audit's grep):
   - If it's per-user data: replace the hardcoded path with a helper call, and add user_id: str as a parameter where it doesn't already flow
   - If it's global system data: replace with system_*_dir() helpers (no user_id needed)

3. Migration script: scripts/migrate_storage_agents.py
   - Moves existing storage_agents/plans/*.json into storage_agents/users/demo/plans/
   - Same for any other per-user folders identified in the audit
   - Idempotent — safe to run twice

4. Tests: any test that touches storage_agents/ paths needs the helper. Use a tmp_path fixture where possible.

5. Commit. Push the branch.

Constraints:
- DO NOT modify SQLAlchemy models or repositories (different agent's job)
- DO NOT modify app_user.py auth logic (different agent's job)
- DO modify nutrition_app/agents/, scripts/, tests/

Output: feat/storage-agents-namespacing branch, paths namespaced, migration script ready.
```

---

## PHASE 3 — Integration (sequential, 1 session)

Wait for all three Phase 2 branches to be pushed. Then:

### Prompt 3 — Integration & Merge (Opus 4.7)

```
You are integrating three parallel feature branches into one cohesive multi-user nutrition app.

Branches to merge into feat/multi-user-foundation:
1. feat/data-layer-multi-user
2. feat/auth-integration
3. feat/storage-agents-namespacing

Goal: get to a state where streamlit run app_user.py boots to a login screen, two users can sign up, and their data is isolated.

Tasks:
1. git checkout feat/multi-user-foundation
2. git merge feat/data-layer-multi-user — should be clean
3. git merge feat/auth-integration — likely conflicts in repository files: data-layer changed implementations, auth changed signatures. Resolve so the signature has user_id as first param AND the body filters by user_id. The TODO comments from auth-integration are obsolete — remove them.
4. git merge feat/storage-agents-namespacing — likely conflicts in agent files where both auth and storage agents added user_id parameters. Keep both changes coherently.
5. After merging, run:
   - pytest — fix anything broken
   - python scripts/init_supabase_schema.py — creates tables in Supabase
   - python scripts/migrate_storage_agents.py — moves existing files
6. Boot the app: streamlit run app_user.py. Verify it loads to a login screen (not a profile page or a crash).
7. If anything's broken: fix it. If you're stuck, document in INTEGRATION_NOTES.md and stop — don't paper over real bugs.
8. git commit, git push.

Critical:
- Conflict resolution should prefer the COMBINATION of both changes, not "pick one side"
- If a repository method ends up with user_id parameter twice (one from each agent), that's a merge artifact — collapse to one
- Don't skip pytest; if 5+ tests fail, that's a sign the contract wasn't followed and needs investigation, not suppression

Output: feat/multi-user-foundation branch, all changes integrated, app boots to login, pytest green.
```

---

## PHASE 4 — Verification (sequential, 1 session)

### Prompt 4 — End-to-End Verification (Sonnet 4.6)

```
You are verifying that a multi-user nutrition app correctly isolates user data.

Setup:
- Branch: feat/multi-user-foundation (already merged from Phase 3)
- App: streamlit run app_user.py (port 8501)
- Two test accounts to create: user_a@test.com / TestPass1!  AND  user_b@test.com / TestPass2!

Goal: prove that user A and user B see ONLY their own data, then document any leaks.

Tasks (manual via the running app — boot it, then drive it via screenshots or by inspecting the database directly):
1. Boot the app. Confirm login screen appears (not the main app).
2. Sign up as user_a@test.com. After login, go to the Profile page and fill in basic biometrics.
3. Go to Inventory and add a food item: "apple, 5 units"
4. Generate a meal plan (Daily Menu page).
5. Log out. Confirm session_state is cleared and login screen returns.
6. Sign up as user_b@test.com. Confirm:
   - Profile is empty (NOT user_a's profile)
   - Inventory is empty (NO apple)
   - No meal plans visible in History
7. As user_b, add "chicken, 2 units" to inventory. Generate a different meal plan.
8. Log out. Log back in as user_a.
9. Confirm: only "apple" in inventory, NOT chicken. Original meal plan still there. Profile data intact.

Database-level verification (in addition to UI):
- Connect to Supabase Postgres via psql or a SQL client.
- SELECT user_id, COUNT(*) FROM inventory GROUP BY user_id; — confirm 2 distinct user IDs, each with their own count
- Same for meal_plans, workout_log, any other user-scoped table

Storage_agents verification:
- ls storage_agents/users/ — confirm two folders, one per user
- Confirm no per-user data leaked into storage_agents/system/

Produce VERIFICATION_REPORT.md with:
- ✅ / ❌ for each step above
- Screenshot or SQL output evidence per step
- Any leaks found (be specific: which table, which method, what got crossed)
- Any UX issues encountered (login flow rough? logout button hard to find?)

If everything passes: commit VERIFICATION_REPORT.md and tag the branch v0.1-demo-ready. The friend demo is unblocked.
If anything fails: document precisely. Do NOT silently fix — the failure is data for the next iteration.
```

---

## Pro tips for running this

1. **Three terminals for Phase 1, three for Phase 2.** Each in a different worktree (`git worktree add`) so they don't share filesystem state.
2. **Pin the model per session** — start each Claude Code session with `--model claude-opus-4-7` or `--model claude-sonnet-4-6` (or your installed equivalents). Wrong model = wasted tokens or insufficient depth.
3. **Phase 1 reports are the contract.** If they're sloppy, Phase 2 will produce sloppy code. Read them before kicking off Phase 2 — 5 min of human review saves 2 hours of refactor.
4. **If Phase 2 agents produce conflicting interpretations of the contract**, that's a Phase 1 audit problem. Fix the audit, re-run Phase 2 from the audit's commit.
5. **Don't skip Phase 4.** "It compiles" ≠ "data is isolated." A leak in production embarrasses you in front of the friend you're demo-ing to.
