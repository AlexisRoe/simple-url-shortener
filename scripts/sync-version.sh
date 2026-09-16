#!/usr/bin/env bash
# Syncs APP_VERSION in .env with the version field from pyproject.toml.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")

touch .env
if grep -q '^APP_VERSION=' .env; then
	sed -i.bak "s/^APP_VERSION=.*/APP_VERSION=${VERSION}/" .env && rm -f .env.bak
else
	printf 'APP_VERSION=%s\n' "${VERSION}" >>.env
fi

echo "APP_VERSION set to ${VERSION} in .env"
