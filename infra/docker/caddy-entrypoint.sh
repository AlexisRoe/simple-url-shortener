#!/bin/sh
# Docker volumes are always created owned by root, even though the image
# itself runs as a non-root user, so chown them here (as root, before
# dropping privileges) rather than baking ownership into the image layer.
set -e

chown -R caddy:caddy /data /config

exec su-exec caddy "$@"
