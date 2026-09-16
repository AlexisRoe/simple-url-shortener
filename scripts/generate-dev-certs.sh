#!/usr/bin/env bash
# Generates a locally-trusted TLS certificate for Caddy's dev config using mkcert.
# mkcert installs a local CA into the macOS system/browser trust stores, so the
# resulting certificate is trusted automatically (no browser warnings).
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v mkcert >/dev/null 2>&1; then
	echo "mkcert is required but not installed. Install it with: brew install mkcert" >&2
	exit 1
fi

CERT_DIR="infra/caddy/certs"
mkdir -p "${CERT_DIR}"

mkcert -install
mkcert -cert-file "${CERT_DIR}/dev.crt" -key-file "${CERT_DIR}/dev.key" localhost 127.0.0.1 ::1

echo "Locally-trusted dev certificate written to ${CERT_DIR}"
