# Bruno API collection

Manual test collection for the redirect API, using [Bruno](https://www.usebruno.com/).

## Requests

- `Ping` / `Status` — unauthenticated health checks.
- `Resolve Short Code` — public `GET /sh/{code}` redirect resolution.
- `redirects/` — full CRUD for redirect management under `/api` (requires auth):
  List Redirects, Create Redirect, Create Variant, Get Redirect, Update Redirect,
  Delete Redirect, Delete All Redirects.

## Steps to test the API

1. Open Bruno and choose **Open Collection**, then select this `bruno/` folder.
2. Select the **local** environment (top-right environment selector) — it sets
   `baseUrl` (`https://localhost:8080`) and `apiToken`.
3. `bruno/environments/local.bru` is gitignored (it holds a real secret) and is
   generated automatically from `local.bru.example` by `make start` /
   `make initial-setup` via `scripts/generate-api-token.sh`, which keeps its
   `apiToken` in sync with `.env`'s `API_TOKEN`. If you haven't run either yet,
   run `make initial-setup` once before opening Bruno.
4. Make sure the app stack is running (e.g. `docker compose up` / `make up`, per
   the project's main README) so `https://localhost:8080` is reachable.
5. All `/api/*` requests use `auth: inherit`, resolving to the collection-level
   bearer auth (`{{apiToken}}`) — no per-request auth setup needed.
6. Run requests individually, or right-click the `redirects` folder and **Run** to
   execute the whole CRUD flow in sequence. A typical flow:
   - `Create Redirect` → copy the returned `code`.
   - `Get Redirect` / `List Redirects` using that code.
   - `Create Variant` for that code.
   - `Update Redirect` (optionally with a `variant` in the body).
   - `Delete Redirect` (single entry) or `Delete All Redirects` (code + all variants).

## Disabling SSL verification (if needed)

The dev stack (`CADDY_ENV=dev`) serves HTTPS using Caddy's internal, locally-trusted
CA rather than a publicly trusted certificate, so Bruno may reject it as untrusted.

SSL verification in Bruno is a global app preference, not a project file setting, so
it can't be committed to this repo — each person testing needs to set it locally:

- **Bruno GUI**: open this collection, click the collection settings (gear icon) →
  **Preferences**, and uncheck **SSL/TLS Certificate Verification**. This can also be
  set globally under the Bruno app menu → **Preferences**.
- **Bruno CLI** (`bru run`): pass `--insecure`, e.g.
  `bru run --insecure --env local redirects`.

Alternatively, instead of disabling verification, you can trust Caddy's local CA
certificate on your machine (it's generated under Caddy's data directory the first
time it runs) so requests to `https://localhost:8080` verify normally.
