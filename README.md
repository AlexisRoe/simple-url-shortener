# simple-url-shortener

A small, self-hosted URL shortener written in Python (FastAPI) backed by
Redis/Valkey, fronted by Caddy for TLS, rate limiting and security headers.

This started as a one-afternoon project to dive deeper into Python
application development and to practice hardening a small service end to
end — auth, input validation, rate limiting, security headers, structured
logging, health checks — rather than just gluing together the "make a
short link" happy path.

It's aimed at small organisations that want an internal link-shortening
tool, particularly for **documentation links that need to resolve
differently depending on the audience**: e.g. `sh.company.internal/onb`
resolving to the English onboarding doc by default, but to a German or
mobile-flavoured variant when a `?variant=` parameter is supplied. Think
"one short code, several flavours" rather than a public link-shrinking
service.

There are many ways to build a URL shortener — this is one deliberately
simple take on it, optimized for being easy to read, run, and reason
about, not for internet-scale traffic.

## Features

- **Short link creation & resolution** — `POST /api` creates a code,
  `GET /sh/{code}` resolves and 302-redirects to its target URL.
- **Variants** — attach alternate target URLs to an existing code
  (`POST /api/{code}/variants`) and select one at resolve time via
  `?variant=`, with a fallback chain: variant URL → base code URL →
  configured default URL. Intended for per-language or per-audience
  documentation links, not statistically-driven A/B testing.
- **Full redirect CRUD** — list (paginated), get, update, delete a single
  entry or a variant, or delete a code and all of its variants at once.
- **Optional TTLs** — any code or variant can be given an expiry (in
  milliseconds); Redis handles the expiry natively.
- **Scoped, expiring bearer tokens** — three roles (`read` <
  `read_write` < `delete`), each its own token with its own expiry;
  a higher-scoped token also satisfies lower-scoped requirements.
  `GET /api/whoami` lets a caller check its own token's remaining
  validity ahead of a sudden 401.
- **Domain allowlisting** — restrict which target domains redirects are
  allowed to point at (`ALLOWED_REDIRECT_DOMAINS`), or allow any https
  URL.
- **HTTPS-only targets** — plain `http://` redirect targets are rejected
  outright (a dedicated error distinguishes "http" from "otherwise
  malformed").
- **Rate limiting** — per-remote-IP, per-zone limits enforced at the
  Caddy layer (`/sh/*`, `/api/*`, everything else each have their own
  budget), with `RateLimit-Policy` headers and a JSON 429 body.
- **Security headers** — HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
  a locked-down `Content-Security-Policy`, `Referrer-Policy: no-referrer`,
  and a stripped `Server` header, all applied at the edge by Caddy.
- **Automatic TLS** — Let's Encrypt in production, a locally-trusted
  self-signed cert for local development, both via Caddy.
- **Structured logging & request correlation** — every request gets an
  `X-Request-ID` (reused if the caller already supplied one), attached to
  every log line emitted while handling that request; text or JSON log
  output.
- **Kubernetes-style health checks** — `/health/livez` (process-only) and
  `/health/readyz` (checks Redis/Valkey, returns 503 when unreachable);
  `/status` remains as a human-facing identity/dependency snapshot.
- **Unified error shape** — every application error (validation, auth,
  not-found, ...) is rendered as the same `{"error": {"code", "message"}}`
  JSON shape, including unexpected exceptions (never a bare traceback).
- **Non-root containers** — both the FastAPI and Caddy images drop to an
  unprivileged user at runtime.
- **Request body size limits** — Caddy rejects oversized bodies at the
  edge (`request_body max_size`), and the app enforces the same limit
  independently for requests that reach it directly (e.g. local
  development without Caddy in front).
- **Authenticated Valkey** — the default Valkey user is disabled; both the
  app and Caddy authenticate with a dedicated ACL username/password
  (`VALKEY_USERNAME`/`VALKEY_PASSWORD`), so network isolation isn't the
  only thing standing between an attacker and every stored short link.

## Getting started (local development)

Requirements: Docker + Docker Compose, and `make`. (The Python
dependency manager is [`uv`](https://docs.astral.sh/uv/), but you don't
need it installed locally unless you want to run tests/lint outside
Docker — see below.)

```bash
git clone https://github.com/AlexisRoe/simple-url-shortener.git
cd simple-url-shortener
make start
```

`make start` runs `initial-setup` for you the first time:

- copies `.env.template` to `.env` if it doesn't exist yet,
- syncs `APP_VERSION` in `.env` from `pyproject.toml`,
- generates three random API tokens (read / read_write / delete) into
  `.env` if they're still at their placeholder value,
- generates a locally-trusted self-signed TLS certificate for Caddy's dev
  config.

...then builds and starts the stack (FastAPI, Valkey, Caddy) in the
background. Once it's up:

- `https://localhost:8080/docs` — interactive API docs (development
  only; disabled in production, see [Limitations](#limitations)).
- `https://localhost:8080/health/readyz` — readiness check.
- `https://localhost:8080/sh/{code}` — resolve a short code.

A [Bruno](https://www.usebruno.com/) collection is included under
`bruno/` with requests for every endpoint, plus a local environment
template (`bruno/environments/local.bru.example`).

Other useful targets:

```bash
make logs    # tail all container logs
make stop    # stop containers, keep volumes
make down    # stop and remove containers
make test    # run the test suite (via uv, no containers needed)
make lint    # ruff check + format check
make check   # test + lint
```

`docker-compose.yml` mounts `src/` into the FastAPI container and runs
`uvicorn --reload`, so code changes are picked up without a rebuild.

## Architecture

```
                        ┌────────────────────────────┐
  Internet/LAN  ──────► │            Caddy            │
                        │  TLS · rate limiting ·      │
                        │  security headers            │
                        └──────────────┬───────────────┘
                                       │ reverse_proxy (internal network)
                                       ▼
                        ┌────────────────────────────┐
                        │      FastAPI (uvicorn)       │
                        │  ┌──────────────────────┐    │
                        │  │ middleware:          │    │
                        │  │  request-id → auth → │    │
                        │  │  access log          │    │
                        │  └──────────┬───────────┘    │
                        │             ▼                │
                        │  routes: /sh  /api  /health  │
                        │           /status  /docs     │
                        │             ▼                │
                        │        use-cases layer       │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌────────────────────────────┐
                        │     Valkey (Redis fork)      │
                        │  sh:<code>            → url  │
                        │  sh:<code>:<variant>  → url  │
                        │  caddy:*              → ACME/│
                        │                     rate-limit│
                        │             state             │
                        └────────────────────────────┘
```

- **Caddy** is the only container with a published host port. It
  terminates TLS, applies per-path rate-limit zones and security headers,
  and reverse-proxies everything to FastAPI over the internal Docker
  network. It also uses Valkey as shared storage for ACME certificates
  and distributed rate-limit counters, via community plugins
  (`caddy-storage-redis`, `caddy-ratelimit`) built into a custom image
  (`infra/docker/caddy.Dockerfile`).
- **FastAPI** is a layered application: `routes/` (HTTP I/O only) →
  `use_cases/` (business logic, one file per operation) → `services/`
  (the Redis client) → `core/` (config, security, errors, logging,
  cross-cutting middleware). Three middlewares run on every request:
  request-ID correlation, bearer-token auth (`/api/*` only), and access
  logging.
- **Valkey** (an open-source Redis fork) is the only datastore. Short
  links are plain string keys (`sh:<code>` and `sh:<code>:<variant>`)
  with Redis-native TTLs; Caddy's ACME state and rate-limit counters live
  in the same instance under a separate `caddy:` key prefix.

See `src/app/` for the code layout and `infra/` for the Caddy/Docker/Valkey
configuration referenced above.

## Technologies used

| Layer                | Technology                                                                   |
| -------------------- | ---------------------------------------------------------------------------- |
| Language / runtime   | Python 3.12                                                                  |
| Web framework        | FastAPI + Uvicorn                                                            |
| Data layer           | Valkey (Redis-compatible) via `redis-py`                                     |
| Reverse proxy / edge | Caddy 2, with `caddy-ratelimit` and `caddy-storage-redis` plugins            |
| Config & validation  | Pydantic / `pydantic-settings`                                               |
| Package management   | `uv`                                                                         |
| Testing              | `pytest`, `httpx`                                                            |
| Linting/formatting   | `ruff`                                                                       |
| Containers           | Docker, Docker Compose                                                       |
| CI                   | GitHub Actions (lint, test, image builds) + Dependabot (uv, Docker, Actions) |
| Manual API testing   | Bruno                                                                        |

## Limitations

This is a deliberately small learning/internal-tool project, not a
hardened public-facing product. Known limitations, and how to mitigate
them if you need to go further:

**Already documented in the codebase/infra:**

- **Only `/sh/*` should ever be public.** `/api/*` (management, bearer-token
  protected), `/docs`, `/openapi.json`, and `/status` should never be
  reachable from the internet — but the app relies on the *reverse
  proxy/network boundary* to enforce that (see `infra/caddy/Caddyfile.prod`).
  A bearer token is not the only line of defense that should stand
  between `/api/*` and the internet; put it behind a firewall rule,
  security group, VPN, or a separate internal-only listener/DNS name.
- **No token rotation or per-user scopes.** The three bearer tokens are
  shared secrets configured once via environment variables — there's no
  mechanism to issue/revoke a token for an individual user, rotate one
  without redeploying, or attribute an API call to a specific person
  beyond "someone with the read/read_write/delete token". Mitigate by
  treating each token as belonging to a small, trusted group, rotating
  them periodically via redeploy, and relying on the request-ID/audit log
  lines if you need to reconstruct who did what around a given time.
- **No IP allowlisting.** Nothing restricts *which* clients may call
  `/api/*` beyond the token itself. Mitigate at the network layer (VPN,
  security group, Caddy `remote_ip` matcher) if the API must be reachable
  outside a fully private network.
- **Per-IP rate limiting only.** Caddy's rate limiter keys on
  `remote.host`, so it's straightforward to spread requests across many
  source IPs (or hide behind a shared NAT/proxy IP and get throttled as a
  group). It stops naive abuse, not a determined or distributed attacker.
- **`GET /api` (list redirects) pages via a secondary index, not a full
  scan.** A `sh:index` ZSET tracks every base code, scored by expiry
  timestamp (`+inf` for codes with no TTL), maintained on
  create/update/delete. Listing reads only the requested page's codes from
  the index, then scans just those codes' keys — it no longer touches the
  full `sh:*` keyspace. As a result, results are ordered by expiry
  (soonest-expiring first, permanent codes last) rather than
  alphabetically. Expired index entries are purged inline on each listing
  call rather than via a background task — sufficient at this app's
  scale; see the note above `purge_expired_index_entries` in
  `redis_client.py` for how to add a periodic sweep if that's ever needed.
  (Note: this only affects the *listing* endpoint — resolving a single
  short code via `GET /sh/{code}` is a direct O(1) key lookup and is
  unaffected.)
- **No metrics or tracing.** There's no Prometheus `/metrics` endpoint or
  OpenTelemetry spans — only structured logs with a per-request duration.
  Deemed overkill for the current scope; the request-logging middleware
  already computes `duration_ms`, which is the natural value to export as
  a histogram first if you need dashboards/alerting.
- **No usage analytics.** Resolutions aren't counted or aggregated
  anywhere (click counts, referrers, geography, etc.) beyond the raw
  access log line for each `/sh/*` request. Anyone needing analytics
  today has to parse logs; a real feature would mean a counter/analytics
  store and almost certainly a privacy/retention policy for it.

**Not yet documented elsewhere — worth knowing about:**

- **Secrets live in a plaintext `.env` file.** Bearer tokens and (in
  production) the ACME email are stored unencrypted on disk and passed
  into containers as plain environment variables — normal for local dev,
  but worth swapping for a real secrets manager (Docker/Swarm secrets,
  Vault, cloud KMS-backed env injection, ...) before running this
  anywhere more sensitive than an internal tool.
- **No image vulnerability scanning in CI.** CI builds both Docker images
  but doesn't scan them (e.g. Trivy/Grype); Dependabot covers dependency
  *updates* but not a point-in-time scan of what's actually in the built
  image. Worth adding a scan step if this is deployed anywhere with a
  compliance requirement.
- **Single Redis/Valkey instance, no HA.** One instance holds every short
  link and all of Caddy's TLS/rate-limit state; RDB snapshots to a Docker
  volume are the only persistence/backup story. There's no replica, no
  off-host backup, and no documented restore procedure. Acceptable for an
  internal tool where losing recent links is inconvenient, not for
  anything where that data must never be lost — add off-host backups (and
  test restoring from one) if that's a requirement for you.

## Contributing

This is a personal learning project, but improvements and bug reports
are welcome. The process is intentionally lightweight:

1. **Open an issue first.** Describe your motivation and exactly what you
   want to fix or change — even a short paragraph is enough. This avoids
   duplicated effort and lets us agree on the approach before any code is
   written.
2. Once there's agreement, you'll be added as a contributor (or can fork
   the repo — either works).
3. **Open a pull request** referencing the issue. Please make sure
   `make check` (tests + lint) passes before requesting review.

## License

See [`LICENSE`](./LICENSE).
