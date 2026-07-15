#!/usr/bin/env python3
"""Make lightweight visualisation subsets of ANFOG glider NetCDF files.

Keeps only the variables needed for trajectory / section plots, applies the
QC mask once (flag <= 2 kept, everything else -> NaN), casts to float32,
and writes compressed NetCDF to anfog_data_viz/.

The output is a DISPOSABLE DERIVATIVE for plotting. QC flags are baked in
and dropped, so "flagged bad" and "never measured" are indistinguishable.
Do science on the originals.

Usage:
    python make_viz_subset.py                # process everything in anfog_data/
    python make_viz_subset.py <file.nc> ...  # process specific files
"""

import sys
from pathlib import Path

import numpy as np
import xarray as xr

try:
    import gsw  # TEOS-10, for potential density
    HAVE_GSW = True
except ImportError:
    HAVE_GSW = False

# Science variables: QC-masked, cast to float32.
# SIGMA0 (potential density) is derived below, not copied.
SCIENCE_VARS = ["TEMP", "PSAL", "DOX2", "CPHL", "BBP", "CDOM"]
# Structural: kept as-is (no QC mask baked in beyond position filtering)
KEEP_EXTRA = ["PROFILE"]
QC_MAX = 2  # IMOS: 1 good, 2 probably good

SRC_DIR = Path(__file__).parent / "anfog_data"
OUT_DIR = Path(__file__).parent / "anfog_data_viz"

# Global attributes worth carrying over
GLOBAL_ATTRS = [
    "title", "platform_code", "deployment_code", "instrument",
    "time_coverage_start", "time_coverage_end",
    "geospatial_lat_min", "geospatial_lat_max",
    "geospatial_lon_min", "geospatial_lon_max",
    "geospatial_vertical_min", "geospatial_vertical_max",
]


def qc_mask(ds: xr.Dataset, var: str) -> xr.DataArray:
    """Return variable with QC > QC_MAX set to NaN. Missing QC var = keep all."""
    qc_name = f"{var}_quality_control"
    da = ds[var]
    if qc_name in ds:
        da = da.where(ds[qc_name] <= QC_MAX)
    return da


def subset_file(src: Path, out: Path) -> tuple[float, float]:
    ds = xr.open_dataset(src, decode_times=True)

    data = {}
    for v in SCIENCE_VARS:
        if v not in ds:
            print(f"    note: {v} not in file, skipping")
            continue
        da = qc_mask(ds, v).astype("float32")
        da.attrs = {k: ds[v].attrs[k] for k in ("standard_name", "long_name", "units")
                    if k in ds[v].attrs}
        da.attrs["comment"] = f"QC flags <= {QC_MAX} kept; others set to NaN. QC baked in."
        data[v] = da

    for v in KEEP_EXTRA:
        if v in ds:
            data[v] = ds[v].astype("float32")
            data[v].attrs = {k: ds[v].attrs[k] for k in ("long_name",) if k in ds[v].attrs}

    # Derived: potential density anomaly sigma0 (TEOS-10), where T and S good.
    if HAVE_GSW and {"TEMP", "PSAL", "PRES"} <= set(ds.data_vars):
        t = qc_mask(ds, "TEMP").values
        sp = qc_mask(ds, "PSAL").values
        p = ds["PRES"].values
        lon, lat = ds["LONGITUDE"].values, ds["LATITUDE"].values
        with np.errstate(invalid="ignore"):
            sa = gsw.SA_from_SP(sp, p, lon, lat)
            ct = gsw.CT_from_t(sa, t, p)
            s0 = gsw.sigma0(sa, ct).astype("float32")
        da = xr.DataArray(s0, dims=ds["TEMP"].dims)
        da.attrs = {"standard_name": "sea_water_sigma_theta",
                    "long_name": "potential density anomaly (sigma-0)",
                    "units": "kg m-3",
                    "comment": "Derived with TEOS-10 (gsw) from QC'd TEMP, PSAL, PRES."}
        data["SIGMA0"] = da

    sub = xr.Dataset(data)

    # Coordinates: positions masked by their own QC, cast float32
    # (float32 ~ 1 m precision at these longitudes - fine for plotting).
    # TIME left at native precision.
    sub = sub.assign_coords(
        TIME=ds.TIME,
        LATITUDE=qc_mask(ds, "LATITUDE").astype("float32"),
        LONGITUDE=qc_mask(ds, "LONGITUDE").astype("float32"),
        DEPTH=qc_mask(ds, "DEPTH").astype("float32"),
    )

    sub.attrs = {k: ds.attrs[k] for k in GLOBAL_ATTRS if k in ds.attrs}
    sub.attrs["source_file"] = src.name
    sub.attrs["processing"] = (
        "Visualisation subset: variable selection, QC mask baked in "
        f"(flag <= {QC_MAX}), float32, zlib compression. NOT for quantitative analysis."
    )

    enc = {v: {"zlib": True, "complevel": 4, "shuffle": True}
           for v in list(sub.data_vars) + ["LATITUDE", "LONGITUDE", "DEPTH"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    sub.to_netcdf(out, encoding=enc)
    ds.close()

    return src.stat().st_size / 1e6, out.stat().st_size / 1e6


def main() -> None:
    if len(sys.argv) > 1:
        files = [Path(a) for a in sys.argv[1:]]
    else:
        files = sorted(SRC_DIR.glob("*/IMOS_ANFOG_*.nc"))
    if not files:
        sys.exit(f"No NetCDF files found under {SRC_DIR}")

    for src in files:
        out = OUT_DIR / f"{src.parent.name}_viz.nc"
        print(f"{src.parent.name}:")
        mb_in, mb_out = subset_file(src, out)
        print(f"    {mb_in:8.1f} MB -> {mb_out:6.1f} MB  ({mb_in/mb_out:4.1f}x)  {out.name}")


if __name__ == "__main__":
    main()
