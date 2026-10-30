#!/bin/zsh
# One-shot Railway deploy for First Rounds. Run from anywhere:  zsh tools/deploy_railway.sh
# Needs: `railway login` done once; .env with NEBIUS_API_KEY + NEBIUS_BASE_URL (never printed).
# Railway CLI 5.x: an empty project needs `railway add --service` before anything can attach to it.
set -e
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"
railway whoami >/dev/null 2>&1 || { echo "not logged in: run  railway login"; exit 1; }
set -a; source .env; set +a
[[ -n "$NEBIUS_API_KEY" ]] || { echo ".env has no NEBIUS_API_KEY"; exit 1; }
SVC=first-rounds
BASE="${NEBIUS_BASE_URL:-https://api.tokenfactory.nebius.com/v1}"

railway status >/dev/null 2>&1 || { echo "creating Railway project $SVC..."; railway init --name "$SVC" < /dev/null; }

if ! railway status 2>/dev/null | grep -q "Service:.*$SVC"; then
  echo "creating service $SVC with its variables (key not shown)..."
  railway add --service "$SVC" \
    --variables "NEBIUS_API_KEY=$NEBIUS_API_KEY" --variables "NEBIUS_BASE_URL=$BASE" \
    --variables "FR_DEMO_ON_START=1" --variables "FR_DB=/srv/data/firstrounds.sqlite" < /dev/null
fi
railway service "$SVC" < /dev/null >/dev/null 2>&1 || true

echo "adding a volume at /srv/data (ok if it already exists)..."
railway volume add --service "$SVC" --mount-path /srv/data < /dev/null 2>/dev/null || true
echo "deploying (builds the Dockerfile on Railway)..."
railway up --detach --service "$SVC" < /dev/null
echo "public domain:"
railway domain --service "$SVC" < /dev/null 2>/dev/null || true
echo
echo "build takes ~2 min. check:  railway status   then open <domain>/api/health"
