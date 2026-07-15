#!/usr/bin/env python
"""
Reduced-aware incremental update — for Nectar, where the raw data is NOT kept.

Decides what to fetch from the *reduced* dataset (anfog_data_viz/), not from the
raw files. A deployment is processed only if its viz subset is missing. For each
new deployment it downloads the raw NetCDF, builds the viz subset, then DELETES
the raw. Finally it rebuilds deployments.js and plotdata/ from all viz files.

    python sync_reduced.py                      # process new deployments, delete raw
    python sync_reduced.py --keep-raw           # keep raw (e.g. a local first pass)
    python sync_reduced.py --fleet slocum_glider --match Forster

So the only bulky thing that persists on Nectar is anfog_data_viz/ (~5x smaller
than raw). Raw NetCDF is transient: downloaded, subset, deleted.
"""

import argparse
import shutil
from pathlib import Path

import fetch_all_anfog as fa
import make_viz_subset as mv
import extract_deployments as ed
import make_plotdata as mp

HERE = Path(__file__).resolve().parent
RAW = HERE / "anfog_data"
VIZ = HERE / "anfog_data_viz"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fleet", choices=fa.FLEETS + ["both"], default="both")
    p.add_argument("--match", default="", help="only deployments whose name contains this")
    p.add_argument("--keep-raw", action="store_true", help="do not delete raw after subsetting")
    a = p.parse_args()
    fleets = fa.FLEETS if a.fleet == "both" else [a.fleet]
    VIZ.mkdir(exist_ok=True)

    processed = skipped = 0
    for fleet, dep in fa.targets(fleets, a.match):
        viz_out = VIZ / f"{dep}_viz.nc"
        if viz_out.exists():
            skipped += 1                       # already in the reduced dataset -> skip
            continue
        ncs = [(k, s) for k, s in fa.list_nc(fleet, dep) if k.endswith(".nc")]
        if not ncs:
            continue

        depdir = RAW / dep
        depdir.mkdir(parents=True, exist_ok=True)
        for key, size in ncs:
            target = depdir / key.split("/")[-1]
            if not (target.exists() and target.stat().st_size == size):
                print(f"  download {size/1e6:7.1f} MB  {dep}/{target.name}")
                fa.s3.download_file(fa.BUCKET, key, str(target))

        for nc in sorted(depdir.glob("IMOS_ANFOG_*.nc")):
            mv.subset_file(nc, viz_out)        # one NetCDF per deployment in practice
        processed += 1
        print(f"  subset -> {viz_out.name}")

        if not a.keep_raw:
            shutil.rmtree(depdir)
            print(f"  deleted raw {depdir.name}/")

    print(f"\n{processed} new deployment(s) processed, {skipped} already in reduced set.")
    if processed:
        print("Rebuilding deployments.js and plotdata/ from the viz files…")
        ed.main()
        mp.main()
        print("Done. Publish the updated deployments.js and plotdata/ to the container.")
    else:
        print("Nothing new — index and plot data unchanged.")


if __name__ == "__main__":
    main()
