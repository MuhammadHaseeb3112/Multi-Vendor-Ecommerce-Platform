#!/usr/bin/env bash
# Update the server to the latest code on GitHub, with a health check and an
# automatic rollback.
#
#   cd ~/markethub && bash deploy/deploy.sh
#
# GitHub Actions runs this over SSH after the tests pass
# (.github/workflows/deploy.yml). It can also be run by hand.
#
# 1. Tag the image that is running now as ":rollback".
# 2. Pull the new code, build, restart.
# 3. Wait for the container health check and for the site through the proxy.
# 4. If either fails: go back to the previous commit and image.
#
# Migrations run on start (docker/entrypoint.sh) and are not undone by a
# rollback, so keep migrations backward compatible (add columns, don't drop or
# rename them in the same release).
set -euo pipefail

# The braces make bash read the whole script before running it: "git reset"
# below replaces this file while it runs.
{
# APP_DIR: the checkout to deploy (set by the GitHub workflow, which runs a
# fresh copy of this script from /tmp). Defaults to the repo this file is in.
cd "${APP_DIR:-$(dirname "$0")/..}"
BRANCH="${DEPLOY_BRANCH:-main}"
ENV_FILE="deploy/.env.prod"
[ -f "$ENV_FILE" ] || { echo "Missing $ENV_FILE (see deploy/DEPLOY.md)"; exit 1; }

# The public domain: first entry of ALLOWED_HOSTS.
DOMAIN="$(grep -E '^ALLOWED_HOSTS=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '"' | cut -d, -f1 | xargs || true)"

COMPOSE=(docker compose -p markethub -f deploy/compose.prod.yml --env-file "$ENV_FILE")
SERVICE="markethub-web"

log() { echo "[deploy $(date +%H:%M:%S)] $*"; }

image() { "${COMPOSE[@]}" config --images | grep -v '^postgres' | head -n1; }

healthy() {
  local container status
  for _ in $(seq 1 48); do
    container="$("${COMPOSE[@]}" ps -q "$SERVICE")"
    status="$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo starting)"
    if [ "$status" = "healthy" ]; then
      # And through the reverse proxy, the way visitors reach it.
      if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "localhost" ]; then
        return 0
      fi
      curl -fsS -o /dev/null --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/login/" && return 0
    fi
    sleep 5
  done
  return 1
}

IMAGE="$(image)"
PREVIOUS="$(git rev-parse HEAD)"
log "Current version: ${PREVIOUS:0:7}"
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "${IMAGE%%:*}:rollback"
fi

git fetch --quiet origin "$BRANCH"
git reset --quiet --hard "origin/$BRANCH"   # deploy/.env.prod is git-ignored, so it stays
CURRENT="$(git rev-parse HEAD)"
log "New version: ${CURRENT:0:7}"

log "Building..."
"${COMPOSE[@]}" build "$SERVICE"
log "Starting..."
"${COMPOSE[@]}" up -d --remove-orphans

if healthy; then
  log "Healthy. Deployed ${CURRENT:0:7}."
  docker image prune -f >/dev/null || true
  exit 0
fi

log "Health check FAILED. Rolling back to ${PREVIOUS:0:7}..."
"${COMPOSE[@]}" logs --tail 80 "$SERVICE" || true
git reset --quiet --hard "$PREVIOUS"
if docker image inspect "${IMAGE%%:*}:rollback" >/dev/null 2>&1; then
  docker tag "${IMAGE%%:*}:rollback" "$IMAGE"
fi
"${COMPOSE[@]}" up -d --remove-orphans
if healthy; then
  log "Rolled back to ${PREVIOUS:0:7}; the site is up on the old version."
else
  log "Rollback did not come up healthy either. Check: ${COMPOSE[*]} logs $SERVICE"
fi
exit 1
}
