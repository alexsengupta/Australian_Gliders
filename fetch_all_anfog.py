#!/usr/bin/env python
"""
Fetch the FULL IMOS ANFOG glider archive (both fleets), not just the sample.

Public data, no AWS account needed:  pip install boto3

    python fetch_all_anfog.py --inventory              # count + total size, no download
    python fetch_all_anfog.py --download               # fetch every NetCDF
    python fetch_all_anfog.py --download --fleet slocum_glider   # one fleet only
    python fetch_all_anfog.py --download --match Forster        # only names containing "Forster"

Resumable: files already present at the right size are skipped, so you can
re-run after an interruption. Raw NetCDFs land in ./anfog_data/<deployment>/,
which is exactly what make_viz_subset.py expects next.
"""

import argparse
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "imos-data"
FLEETS = ["slocum_glider", "seaglider"]
OUTDIR = Path("./anfog_data")

s3 = boto3.client("s3", region_name="ap-southeast-2",
                  config=Config(signature_version=UNSIGNED))


def list_deployments(fleet):
    """Top-level deployment folder names under a fleet, via CommonPrefixes."""
    names = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"IMOS/ANFOG/{fleet}/",
                                   Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            names.append(cp["Prefix"].rstrip("/").split("/")[-1])
    return names


def list_nc(fleet, dep):
    """(key, size) for every .nc under one deployment."""
    out = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"IMOS/ANFOG/{fleet}/{dep}/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".nc"):
                out.append((obj["Key"], obj["Size"]))
    return out


def targets(fleets, match):
    for fleet in fleets:
        for dep in list_deployments(fleet):
            if match and match.lower() not in dep.lower():
                continue
            yield fleet, dep


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", action="store_true", help="count and size only")
    p.add_argument("--download", action="store_true", help="download the NetCDFs")
    p.add_argument("--fleet", choices=FLEETS + ["both"], default="both")
    p.add_argument("--match", default="", help="only deployments whose name contains this")
    a = p.parse_args()
    if not (a.inventory or a.download):
        p.print_help(); return

    fleets = FLEETS if a.fleet == "both" else [a.fleet]
    n_dep = n_file = 0
    bytes_total = bytes_got = 0

    for fleet, dep in targets(fleets, a.match):
        ncs = list_nc(fleet, dep)
        if not ncs:
            continue
        n_dep += 1
        for key, size in ncs:
            n_file += 1
            bytes_total += size
            if a.download:
                dest = OUTDIR / dep
                dest.mkdir(parents=True, exist_ok=True)
                target = dest / key.split("/")[-1]
                if target.exists() and target.stat().st_size == size:
                    continue
                print(f"  {size/1e6:7.1f} MB  {fleet}/{dep}/{target.name}")
                s3.download_file(BUCKET, key, str(target))
                bytes_got += size

    print(f"\n{n_dep} deployments, {n_file} NetCDF files, "
          f"{bytes_total/2**30:.1f} GiB total.")
    if a.download:
        print(f"Downloaded {bytes_got/2**30:.2f} GiB of new data into {OUTDIR}/ "
              f"(the rest was already present).")
    else:
        print("Inventory only — re-run with --download to fetch.")


if __name__ == "__main__":
    main()
