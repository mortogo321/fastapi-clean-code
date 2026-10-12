# syntax=docker/dockerfile:1

FROM oven/bun:1.4.3-alpine AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM oven/bun:1.4.3-alpine AS builder
ARG ENV=production
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY package.json bunfig.toml next.config.ts tsconfig.json postcss.config.mjs ./
COPY src ./src
COPY .env.${ENV} .env
RUN bun run build

# Development target (compose.dev.yml): next dev with Compose Watch syncing src. Not the default target.
FROM oven/bun:1.4.3-alpine AS dev
ARG ENV=development
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
RUN chown bun:bun /app
COPY --chown=bun:bun --from=deps /app/node_modules ./node_modules
COPY --chown=bun:bun package.json bunfig.toml next.config.ts tsconfig.json postcss.config.mjs ./
COPY --chown=bun:bun src ./src
COPY --chown=bun:bun .env.${ENV} .env
USER bun
EXPOSE 3000
CMD ["bun", "run", "dev", "-H", "0.0.0.0"]

FROM oven/bun:1.4.3-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
# The app stays root-owned and read-only for the runtime user; only the cache is writable.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/.env ./.env
COPY bunfig.toml ./
RUN mkdir -p .next/cache && chown bun:bun .next/cache
USER bun
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/healthz > /dev/null || exit 1
CMD ["bun", "server.js"]
