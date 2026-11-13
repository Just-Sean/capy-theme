# .github/workflows/ci.yml

**What it is:** the CI (continuous integration) workflow. It runs on every pull request and every push to `main`, so each PR shows passing or failing checks before it's merged. It repeats the local checks on GitHub, because local hooks can be skipped.

**Its four jobs:**

1. **Lint (ruff):** installs the exact locked dependencies (`uv sync --locked`), then runs `ruff check` and `ruff format --check`.
2. **Tests (sqlite) and Tests (postgres):** the full test suite twice, once on SQLite and once on a throwaway Postgres 17 database.
   - It first downloads the Tailwind CLI and checks its SHA-256 against a known value, so the daisyUI build test really runs and runs the genuine file.
   - Tests run with coverage, and the job fails below 80%.
   - `-rs` lists any skipped tests.
3. **Dependency vulnerabilities (pip-audit):** exports the locked dependencies with their hashes and checks them against known-vulnerability databases.
4. **Secrets (gitleaks, whole history):** scans every commit ever made for passwords, keys or tokens, using a gitleaks Docker image pinned by digest.

**Security details:**

- Every action is pinned to a commit hash, not a tag, because tags can be moved.
- The workflow only has read access to the repo.
- Checkout doesn't keep git credentials.
- The Postgres password is for a database that exists only during the job.

**Keep in step:**

- `UV_VERSION` with the uv you use locally.
- `GITLEAKS_IMAGE` with the README's gitleaks commands.
- `TAILWIND_CLI` and its SHA-256 with `TAILWIND_CLI_VERSION` in `demo/demo_site/settings.py`.
