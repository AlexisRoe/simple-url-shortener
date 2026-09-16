# simple-url-shortener
A simple url shortener build in Python using Redis

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
