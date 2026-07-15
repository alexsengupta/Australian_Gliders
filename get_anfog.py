#!/usr/bin/env python
"""
Download and inspect a handful of IMOS ANFOG glider deployments.

Public data, no AWS account or credentials needed.
    pip install boto3 xarray netcdf4

Usage:
    python get_anfog.py --inventory     # look, don't download
    python get_anfog.py --download      # fetch the NetCDFs
    python get_anfog.py --inspect       # summarise what was fetched
"""

import argparse
import os
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "imos-data"
FLEET = "slocum_glider"          # or "seaglider"

# Three Forster (NSW shelf, EAC) deployments across different seasons.
# Edit this list to point somewhere else.
DEPLOYMENTS = [
    "Forster20240517",   # autumn / early winter
    "Forster20241030",   # spring
    "Forster20250225",   # late summer
]

OUTDIR = Path("./anfog_data")

s3 = boto3.client("s3", region_name="ap-southeast-2",
                  config=Config(signature_version=UNSIGNED))


def list_objects(prefix):
    """All objects under a prefix, as (key, size_bytes)."""
    out = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            out.append((obj["Key"], obj["Size"]))
    return out


def deployment_prefix(dep):
    return f"IMOS/ANFOG/{FLEET}/{dep}/"


def inventory():
    """Print the full contents of each deployment folder, so we can see
    what is actually there rather than guessing at the conventions."""
    for dep in DEPLOYMENTS:
        objs = list_objects(deployment_prefix(dep))
        if not objs:
            print(f"\n{dep}: NOTHING FOUND — check the name and fleet\n")
            continue

        nc = [(k, s) for k, s in objs if k.endswith(".nc")]
        other = [(k, s) for k, s in objs if not k.endswith(".nc")]

        print(f"\n=== {dep} ===")
        print(f"  {len(objs)} objects, {sum(s for _, s in objs)/1e6:.1f} MB total")
        print(f"  NetCDF: {len(nc)} files, {sum(s for _, s in nc)/1e6:.1f} MB")
        for k, s in nc:
            print(f"    {s/1e6:8.1f} MB  {k.split('/')[-1]}")
        if other:
            print(f"  Non-NetCDF: {len(other)} files, "
                  f"{sum(s for _, s in other)/1e6:.1f} MB "
                  f"(e.g. {other[0][0].split('/')[-1]})")


def download():
    """Fetch only the NetCDFs. Plots and logs are skipped."""
    total = 0
    for dep in DEPLOYMENTS:
        dest = OUTDIR / dep
        dest.mkdir(parents=True, exist_ok=True)
        for key, size in list_objects(deployment_prefix(dep)):
            if not key.endswith(".nc"):
                continue
            target = dest / key.split("/")[-1]
            if target.exists() and target.stat().st_size == size:
                print(f"  skip (have it)  {target.name}")
                continue
            print(f"  get {size/1e6:7.1f} MB  {target.name}")
            s3.download_file(BUCKET, key, str(target))
            total += size
    print(f"\nDownloaded {total/1e6:.1f} MB into {OUTDIR}/")


def inspect():
    """Open each file and report what is inside it."""
    import xarray as xr

    for path in sorted(OUTDIR.rglob("*.nc")):
        print(f"\n=== {path.relative_to(OUTDIR)} ===")
        try:
            ds = xr.open_dataset(path)
        except Exception as e:
            print(f"  could not open: {e}")
            continue

        print(f"  dims: {dict(ds.sizes)}")

        # What is actually measured, as opposed to QC flags and coordinates
        measured = [v for v in ds.data_vars if not v.endswith("_quality_control")]
        print(f"  variables: {', '.join(measured)}")

        for coord in ("TIME", "DEPTH", "LATITUDE", "LONGITUDE"):
            if coord in ds:
                v = ds[coord].values
                try:
                    print(f"  {coord:10s} {v.min()}  ->  {v.max()}")
                except (TypeError, ValueError):
                    pass

        # The QC convention matters: IMOS uses 1=good, 2=probably good,
        # 3=probably bad, 4=bad, 9=missing. Anything >2 should be treated
        # with suspicion, and a lot of code silently ignores this.
        for v in ds.data_vars:
            if v.endswith("_quality_control"):
                import numpy as np
                flags, counts = np.unique(ds[v].values, return_counts=True)
                frac_good = counts[flags <= 2].sum() / counts.sum()
                print(f"  QC {v[:-len('_quality_control')]:8s} "
                      f"flags={dict(zip(flags.tolist(), counts.tolist()))} "
                      f"good={frac_good:.1%}")

        ds.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", action="store_true")
    p.add_argument("--download", action="store_true")
    p.add_argument("--inspect", action="store_true")
    a = p.parse_args()

    if a.inventory:
        inventory()
    if a.download:
        download()
    if a.inspect:
        inspect()
    if not (a.inventory or a.download or a.inspect):
        p.print_help()
