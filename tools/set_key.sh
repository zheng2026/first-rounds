#!/bin/zsh
# Paste the Nebius Token Factory key once (hidden), store it in .env (chmod 600), verify it, never print it.
# Run from the project folder:  zsh tools/set_key.sh
set -e
cd "$(dirname "$0")/.."
read -s "KEY?Paste your Nebius Token Factory API key (hidden), then Enter: "
echo
if [[ -z "$KEY" ]]; then echo "nothing pasted, .env unchanged"; exit 1; fi
umask 077
printf 'NEBIUS_API_KEY=%s\nNEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1\n' "$KEY" > .env
chmod 600 .env
echo "saved to .env (mode 600). verifying..."
code=$(curl -s -o /tmp/fr_models.json -w '%{http_code}' -H "Authorization: Bearer $KEY" https://api.tokenfactory.nebius.com/v1/models)
unset KEY
if [[ "$code" != "200" ]]; then echo "verify FAILED: HTTP $code (wrong/stale key?)"; rm -f /tmp/fr_models.json; exit 1; fi
echo "key OK. Nemotron models visible to this key:"
python3 -I -c 'import json;[print("  "+m["id"]) for m in json.load(open("/tmp/fr_models.json"))["data"] if "emotron" in m["id"]]'
rm -f /tmp/fr_models.json
