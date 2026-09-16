FROM caddy:2-builder-alpine AS builder

RUN xcaddy build \
	--with github.com/mholt/caddy-ratelimit \
	--with github.com/pberkel/caddy-storage-redis

FROM caddy:2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
