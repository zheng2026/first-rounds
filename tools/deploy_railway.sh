#!/bin/zsh
# One-shot Railway deploy for First Rounds. Run from anywhere:  zsh tools/deploy_railway.sh
# Needs: `railway login` done once; .env with NEBIUS_API_KEY + NEBIUS_BASE_URL (never printed).
set -e
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"
railway whoami >/dev/null 2>&1 || { echo "not logged in: run  railway login"; exit 1; }
set -a; source .env; set +a
[[ -n "$NEBIUS_API_KEY" ]] || { echo ".env has no NEBIUS_API_KEY"; exit 1; }

if [[ ! -f .railway/config.json && -z "$(railway status 2>/dev/null | grep -i project)" ]]; then
  echo "creating Railway project first-rounds..."
  railway init --name first-rounds < /dev/null
fi
echo "setting variables (key not shown)..."
railway variables --set "NEBIUS_API_KEY=$NEBIUS_API_KEY" --set "NEBIUS_BASE_URL=${NEBIUS_BASE_URL:-https://api.tokenfactory.nebius.com/v1}" \
  --set "FR_DEMO_ON_START=1" --set "FR_DB=/srv/data/firstrounds.sqlite" --skip-deploys >/dev/null
echo "adding a volume at /srv/data (ok if it already exists)..."
railway volume add --mount-path /srv/data < /dev/null 2>/dev/null || true
echo "deploying (builds the Dockerfile on Railway)..."
railway up --detach < /dev/null
echo "public domain:"
railway domain < /dev/null 2>/dev/null || true
echo
echo "when the build finishes (~2 min), check:  railway status   and open the domain above (/api/health first)."
