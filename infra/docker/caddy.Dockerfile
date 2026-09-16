FROM caddy:2-builder-alpine@sha256:1a1689db91cfb390b2d856a1b3774e796852822cd723fa54c475b272f82bb4b7 AS builder

RUN xcaddy build \
	--with github.com/mholt/caddy-ratelimit@v0.1.0 \
	--with github.com/pberkel/caddy-storage-redis@v1.8.2

FROM caddy:2-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# cap_net_bind_service lets the caddy binary bind to privileged ports (80/443)
# without the process running as root. su-exec drops to the non-root caddy
# user at start, after the entrypoint has chowned the mounted data/config
# volumes (which docker always creates owned by root).
RUN addgroup -S caddy && adduser -S -G caddy -D caddy && \
	apk add --no-cache libcap su-exec && \
	setcap cap_net_bind_service=+ep /usr/bin/caddy && \
	apk del libcap

COPY infra/docker/caddy-entrypoint.sh /usr/local/bin/caddy-entrypoint.sh
RUN chmod +x /usr/local/bin/caddy-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/caddy-entrypoint.sh"]
