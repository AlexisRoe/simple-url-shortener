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
CERT_FILE="${CERT_DIR}/dev.crt"
KEY_FILE="${CERT_DIR}/dev.key"
MIN_DAYS_VALID=30

mkdir -p "${CERT_DIR}"

if [[ -f "${CERT_FILE}" && -f "${KEY_FILE}" ]]; then
	if openssl x509 -checkend "$((MIN_DAYS_VALID * 86400))" -noout -in "${CERT_FILE}" >/dev/null 2>&1; then
		echo "Existing dev certificate at ${CERT_FILE} is still valid for more than ${MIN_DAYS_VALID} days, skipping."
		exit 0
	fi
	echo "Existing dev certificate is missing, expired, or expiring soon, regenerating."
fi

mkcert -install
mkcert -cert-file "${CERT_FILE}" -key-file "${KEY_FILE}" localhost 127.0.0.1 ::1

echo "Locally-trusted dev certificate written to ${CERT_DIR}"
