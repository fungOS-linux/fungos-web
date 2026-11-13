#!/bin/sh
# Rebuild the site tree locally: optionally regenerate docs HTML from
# docs-source/, then reinstall the shared theme bundle into the publish
# directory. Inputs come from fab.toml.
#
#   scripts/build.sh           theme bundle only (no code checkouts needed)
#   scripts/build.sh --docs    also regenerate docs HTML
#
# Document regeneration checks the code checkouts named in the docs manifest, so
# it needs them laid out beside this repository. Commit the canonical Markdown
# first; see README.md.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

docs=0
for arg in "$@"; do
  case "$arg" in
    --docs) docs=1 ;;
    *) echo "build.sh: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# publish_dir, theme_dir, theme_project, docs_manifest
set -- $(python3 - "$root/fab.toml" <<'PY'
import sys, tomllib

with open(sys.argv[1], "rb") as handle:
    contract = tomllib.load(handle)

for value in (
    contract["site"]["publish_dir"],
    contract["build"]["theme_dir"],
    contract["build"]["theme_project"],
    contract["build"]["docs_manifest"],
):
    print(value)
PY
)
publish_dir=$root/$1
theme_rel=$2
theme_project=$3
docs_manifest=$4

# A sibling checkout is the documented layout; FPL_THEME_DIR wins so a bare
# clone on a workstation can still build.
theme=${FPL_THEME_DIR:-}
if [ -z "$theme" ]; then
  for candidate in "$root/$theme_rel" "$HOME/src/fpl-project-theme"; do
    if [ -d "$candidate" ]; then
      theme=$candidate
      break
    fi
  done
fi

if [ -z "$theme" ] || [ ! -d "$theme" ]; then
  echo "build.sh: theme checkout not found; set FPL_THEME_DIR to a fpl-project-theme checkout" >&2
  exit 1
fi

cd "$theme"

if [ "$docs" -eq 1 ]; then
  cargo run --quiet --bin docs -- --manifest "$root/$docs_manifest"
fi

cargo run --quiet -- --site "$publish_dir" --project "$theme_project"
