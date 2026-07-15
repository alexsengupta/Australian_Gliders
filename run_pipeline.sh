#!/usr/bin/env bash
# Build the whole app dataset from scratch: download -> subset -> manifest -> plot data.
# Run inside the conda env:  conda activate gliders && ./run_pipeline.sh
#
# Pass extra args straight through to the downloader, e.g. to scope the pull:
#   ./run_pipeline.sh --fleet slocum_glider          # Slocum only
#   ./run_pipeline.sh --match Forster                 # just Forster missions
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/4  Downloading raw NetCDF (the slow part) =="
python fetch_all_anfog.py --download "$@"

echo "== 2/4  Building visualisation subsets (anfog_data_viz/) =="
python make_viz_subset.py

echo "== 3/4  Building deployment manifest (deployments.js) =="
python extract_deployments.py

echo "== 4/4  Building per-deployment plot data (plotdata/) =="
python make_plotdata.py

echo "Done. Open glider_map.html in a browser."
