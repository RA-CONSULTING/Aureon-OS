# Aureon SaaS console — production frontend image.
#   docker build -f deploy/frontend.Dockerfile -t aureon-frontend .
#
# Multi-stage: node builds the Vite bundle, nginx serves it and proxies /api
# to the operator gateway (deploy/frontend.nginx.conf). VITE_* values are
# baked at build time — pass them as --build-arg (compose wires them from env).

FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

# Production defaults: auth-gate the console, fetch manifests live via /api.
ARG VITE_REQUIRE_AUTH=1
ARG VITE_AUREON_MANIFEST_BASE=/api/manifests
ARG VITE_SUPABASE_URL=
ARG VITE_SUPABASE_PUBLISHABLE_KEY=
ARG VITE_LOCAL_TERMINAL_URL=
ARG VITE_NEXUS_SOCKET_URL=
ENV VITE_REQUIRE_AUTH=$VITE_REQUIRE_AUTH \
    VITE_AUREON_MANIFEST_BASE=$VITE_AUREON_MANIFEST_BASE \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY \
    VITE_LOCAL_TERMINAL_URL=$VITE_LOCAL_TERMINAL_URL \
    VITE_NEXUS_SOCKET_URL=$VITE_NEXUS_SOCKET_URL

RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/frontend.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD wget -qO /dev/null http://localhost/ || exit 1
