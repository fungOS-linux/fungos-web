#!/bin/sh
# Serve the published site tree on loopback.
#
# `fab-sites` is the same static artifact proxy that serves Fab sites in the
# cluster; here it reads the local route manifest `scripts/publish.py` writes
# and serves the CID-addressed tree from the local site store. The Mycelium
# gateway fronts this address under the ingress name.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# state_dir, bind
set -- $(python3 - "$root/fab.toml" <<'PY'
import os, sys, tomllib

with open(sys.argv[1], "rb") as handle:
    contract = tomllib.load(handle)

print(os.path.expanduser(contract["publish"]["state_dir"]))
print(contract["ingress"]["bind"])
PY
)

state=${FUNGOS_SITE_STATE:-$1}
bind=${FUNGOS_SITE_BIND:-$2}

if [ ! -s "$state/manifest.json" ]; then
  echo "serve.sh: no publish manifest in $state; run scripts/publish.py first" >&2
  exit 1
fi

if [ -n "${FAB_SITES_BIN:-}" ]; then
  bin=$FAB_SITES_BIN
elif command -v fab-sites >/dev/null 2>&1; then
  bin=$(command -v fab-sites)
elif [ -x "$HOME/src/fpl/fab/target/release/fab-sites" ]; then
  bin=$HOME/src/fpl/fab/target/release/fab-sites
else
  echo "serve.sh: fab-sites not found" >&2
  echo "serve.sh: build it in a fab checkout with 'cargo build -p fab-sites --release', or set FAB_SITES_BIN" >&2
  exit 1
fi

exec "$bin" \
  --bind-addr "$bind" \
  --manifest-path "$state/manifest.json" \
  --local-artifact-root "$state"
