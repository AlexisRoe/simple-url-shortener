# simple-url-shortener
A simple url shortener build in Python using Redis

## Health checks

- `GET /health/livez` -- liveness (Kubernetes-style, `-z` suffix by
  convention). Process-only, no dependency checks; an orchestrator should
  restart the container only when this fails.
- `GET /health/readyz` -- readiness. Checks Redis/Valkey; returns 503 when
  unreachable so the instance is pulled out of rotation without being
  restarted. `docker-compose.yml`'s `fastapi` healthcheck uses this one.
- `GET /status` -- human-facing app identity + dependency snapshot, kept
  for backwards compatibility. Not intended for orchestrator probes.

## Observability

Every request is assigned a request ID (from an incoming `X-Request-ID`
header if present, otherwise generated), which is attached to every log
line emitted while handling that request and echoed back in the
`X-Request-ID` response header -- see `app.core.request_context` and
`app.core.middleware.add_request_id`.

Metrics/tracing (e.g. a Prometheus `/metrics` endpoint or OpenTelemetry
spans) are intentionally not implemented -- overkill for this app's
current scope as an internal tool. Worth revisiting if/when this needs
dashboards or alerting; `log_requests` already computes a per-request
duration that would be the natural value to export first.
