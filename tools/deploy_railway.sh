#!/bin/zsh
# One-shot Railway deploy for First Rounds. Run from anywhere:  zsh tools/deploy_railway.sh
# Needs: `railway login` done once; .env with NEBIUS_API_KEY + NEBIUS_BASE_URL (never printed).
# Order matters: a new Railway project has no service until the first `railway up`; variables/volume/domain attach to it.
set -e
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"
railway whoami >/dev/null 2>&1 || { echo "not logged in: run  railway login"; exit 1; }
set -a; source .env; set +a
[[ -n "$NEBIUS_API_KEY" ]] || { echo ".env has no NEBIUS_API_KEY"; exit 1; }
SVC=first-rounds

railway status >/dev/null 2>&1 || { echo "creating Railway project $SVC..."; railway init --name "$SVC" < /dev/null; }

if ! railway status 2>/dev/null | grep -q "$SVC"; then
  echo "first deploy (creates the service and builds the Dockerfile on Railway)..."
  railway up --detach --service "$SVC" < /dev/null 2>/dev/null || railway up --detach < /dev/null
fi
railway service "$SVC" < /dev/null >/dev/null 2>&1 || true

echo "setting variables (key not shown)..."
railway variables --service "$SVC" --set "NEBIUS_API_KEY=$NEBIUS_API_KEY" \
  --set "NEBIUS_BASE_URL=${NEBIUS_BASE_URL:-https://api.tokenfactory.nebius.com/v1}" \
  --set "FR_DEMO_ON_START=1" --set "FR_DB=/srv/data/firstrounds.sqlite" --skip-deploys >/dev/null
echo "adding a volume at /srv/data (ok if it already exists)..."
railway volume add --service "$SVC" --mount-path /srv/data < /dev/null 2>/dev/null || true
echo "deploying with the variables in place..."
railway up --detach --service "$SVC" < /dev/null
echo "public domain:"
railway domain --service "$SVC" < /dev/null 2>/dev/null || railway domain < /dev/null 2>/dev/null || true
echo
echo "build takes ~2 min. check:  railway status   then open <domain>/api/health"
