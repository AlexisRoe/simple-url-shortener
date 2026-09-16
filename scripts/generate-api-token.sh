#!/usr/bin/env bash
# Ensures .env has a real, random API_TOKEN (never the .env.template placeholder)
# and mirrors it into bruno/environments/local.bru so the Bruno collection works
# out of the box without ever committing a real secret to git.
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env"
PLACEHOLDER="change-me-to-a-long-random-secret"
BRUNO_ENV_FILE="bruno/environments/local.bru"
BRUNO_ENV_EXAMPLE="bruno/environments/local.bru.example"

touch "${ENV_FILE}"
if ! grep -q '^API_TOKEN=' "${ENV_FILE}"; then
	printf 'API_TOKEN=%s\n' "${PLACEHOLDER}" >>"${ENV_FILE}"
fi

CURRENT_TOKEN=$(grep '^API_TOKEN=' "${ENV_FILE}" | head -n1 | cut -d= -f2-)

if [[ -z "${CURRENT_TOKEN}" || "${CURRENT_TOKEN}" == "${PLACEHOLDER}" ]]; then
	CURRENT_TOKEN=$(openssl rand -hex 32)
	sed -i.bak "s/^API_TOKEN=.*/API_TOKEN=${CURRENT_TOKEN}/" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
	echo "Generated a new API_TOKEN in ${ENV_FILE}"
fi

if [[ ! -f "${BRUNO_ENV_FILE}" ]]; then
	cp "${BRUNO_ENV_EXAMPLE}" "${BRUNO_ENV_FILE}"
fi

sed -i.bak "s/^  apiToken: .*/  apiToken: ${CURRENT_TOKEN}/" "${BRUNO_ENV_FILE}" && rm -f "${BRUNO_ENV_FILE}.bak"

echo "Synced API_TOKEN into ${BRUNO_ENV_FILE}"
