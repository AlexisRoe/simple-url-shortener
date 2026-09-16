#!/usr/bin/env bash
# Ensures .env has three real, random, scoped API tokens (read / read_write /
# delete), each with an expiry, and mirrors them into
# bruno/environments/local.bru so the Bruno collection works out of the box
# without ever committing a real secret to git. Also ensures .env has a real,
# random VALKEY_PASSWORD (the ACL credential Valkey/Caddy authenticate with;
# see infra/valkyr/valkyr.conf).
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env"
PLACEHOLDER="change-me-to-a-long-random-secret"
BRUNO_ENV_FILE="bruno/environments/local.bru"
BRUNO_ENV_EXAMPLE="bruno/environments/local.bru.example"

# 90 days from now, in UTC, ISO 8601 -- works on both GNU date (Linux) and
# BSD date (macOS), which take incompatible flags for relative dates.
default_expiry() {
	date -u -d "+90 days" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
		|| date -u -v+90d +"%Y-%m-%dT%H:%M:%SZ"
}

touch "${ENV_FILE}"

if ! grep -q "^VALKEY_USERNAME=" "${ENV_FILE}"; then
	printf 'VALKEY_USERNAME=shortener\n' >>"${ENV_FILE}"
fi

if ! grep -q "^VALKEY_PASSWORD=" "${ENV_FILE}"; then
	printf 'VALKEY_PASSWORD=%s\n' "${PLACEHOLDER}" >>"${ENV_FILE}"
fi

CURRENT_VALKEY_PASSWORD=$(grep "^VALKEY_PASSWORD=" "${ENV_FILE}" | head -n1 | cut -d= -f2-)

if [[ -z "${CURRENT_VALKEY_PASSWORD}" || "${CURRENT_VALKEY_PASSWORD}" == "${PLACEHOLDER}" ]]; then
	CURRENT_VALKEY_PASSWORD=$(openssl rand -hex 32)
	sed -i.bak "s/^VALKEY_PASSWORD=.*/VALKEY_PASSWORD=${CURRENT_VALKEY_PASSWORD}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
	echo "Generated a new VALKEY_PASSWORD in ${ENV_FILE}"
fi

DELETE_TOKEN=""

for ROLE in READ READ_WRITE DELETE; do
	TOKEN_VAR="API_TOKEN_${ROLE}"
	EXPIRES_VAR="API_TOKEN_${ROLE}_EXPIRES_AT"

	if ! grep -q "^${TOKEN_VAR}=" "${ENV_FILE}"; then
		printf '%s=%s\n' "${TOKEN_VAR}" "${PLACEHOLDER}" >>"${ENV_FILE}"
	fi
	if ! grep -q "^${EXPIRES_VAR}=" "${ENV_FILE}"; then
		printf '%s=%s\n' "${EXPIRES_VAR}" "$(default_expiry)" >>"${ENV_FILE}"
	fi

	CURRENT_TOKEN=$(grep "^${TOKEN_VAR}=" "${ENV_FILE}" | head -n1 | cut -d= -f2-)

	if [[ -z "${CURRENT_TOKEN}" || "${CURRENT_TOKEN}" == "${PLACEHOLDER}" ]]; then
		CURRENT_TOKEN=$(openssl rand -hex 32)
		sed -i.bak "s/^${TOKEN_VAR}=.*/${TOKEN_VAR}=${CURRENT_TOKEN}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
		echo "Generated a new ${TOKEN_VAR} in ${ENV_FILE}"
	fi

	if [[ "${ROLE}" == "DELETE" ]]; then
		DELETE_TOKEN="${CURRENT_TOKEN}"
	fi
done

if [[ ! -f "${BRUNO_ENV_FILE}" ]]; then
	cp "${BRUNO_ENV_EXAMPLE}" "${BRUNO_ENV_FILE}"
fi

# The Bruno collection authenticates every request with a single
# {{apiToken}} variable, so point it at the highest-scoped (delete) token,
# which the read/read_write hierarchy also lets satisfy any request.
sed -i.bak "s/^  apiToken: .*/  apiToken: ${DELETE_TOKEN}/" "${BRUNO_ENV_FILE}" && rm -f "${BRUNO_ENV_FILE}.bak"

echo "Synced API tokens into ${BRUNO_ENV_FILE}"
