#!/usr/bin/env bash
# Build the per-client folder of the interactive CRM guide (site/crm-guide) for publishing as a claude.ai artifact.
# Usage: scripts/pp_crm_guide_site.sh <slug> "<Short name>" <out_dir>
#   (run scripts/pp_crm_guide.py <slug> first so site/crm-guide/data/<slug>.json is current)
# Publish: Artifact file_path=<out_dir>/index.html, files {data.json, logo.png}, capabilities {db:{}, user:{}}.
set -euo pipefail
slug="$1"; name="$2"; out="$3"
root="$(cd "$(dirname "$0")/.." && pwd)/site/crm-guide"
[ -f "$root/data/$slug.json" ] || { echo "missing $root/data/$slug.json (run pp_crm_guide.py $slug)"; exit 1; }
mkdir -p "$out"
sed "s|<title>CRM Launch Guide</title>|<title>$name CRM Guide</title>|" "$root/index.html" > "$out/index.html"
cp "$root/data/$slug.json" "$out/data.json"
cp "$root/logo.png" "$out/logo.png"
echo "built $out"
