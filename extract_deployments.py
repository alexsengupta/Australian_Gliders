#!/usr/bin/env python3
"""Build the deployment manifest for the glider map app.

Reads every *_viz.nc in anfog_data_viz/ and writes deployments.js:
one summary record per deployment (launch position, dates, vehicle,
basic stats). The map app (glider_map.html) renders this manifest.

To extend to the full archive: run make_viz_subset.py on more files,
then rerun this. The app needs no changes.

Written as a .js file (not .json) so glider_map.html works when opened
directly from disk (file://), where browsers block JSON fetch.
"""

import json
from pathlib import Path

import numpy as np
import xarray as xr

VIZ_DIR = Path(__file__).parent / "anfog_data_viz"
OUT = Path(__file__).parent / "deployments.js"


def first_finite(lat, lon):
    ok = np.isfinite(lat) & np.isfinite(lon)
    i = int(np.argmax(ok))
    if not ok[i]:
        return None, None
    return float(lat[i]), float(lon[i])


def summarise(path: Path) -> dict:
    ds = xr.open_dataset(path)
    lat, lon = ds.LATITUDE.values, ds.LONGITUDE.values
    launch_lat, launch_lon = first_finite(lat, lon)
    ok = np.isfinite(lat) & np.isfinite(lon)
    i_last = len(lat) - 1 - int(np.argmax(ok[::-1]))

    t0 = np.datetime_as_string(ds.TIME.values[0], unit="D")
    t1 = np.datetime_as_string(ds.TIME.values[-1], unit="D")
    days = float((ds.TIME.values[-1] - ds.TIME.values[0]) / np.timedelta64(1, "D"))

    platform = str(ds.attrs.get("platform_code", "?"))
    # ANFOG fleet is two vehicle types. Slocum hull codes start "SL"; the deep
    # ~1000 m Seagliders are the other class. Refine this when going national.
    vehicle = "Slocum" if platform.upper().startswith("SL") else "Seaglider"
    rec = {
        "id": path.stem.replace("_viz", ""),
        "platform": platform,
        "vehicle": vehicle,
        "launch_lat": launch_lat,
        "launch_lon": launch_lon,
        "end_lat": float(lat[i_last]) if ok[i_last] else None,
        "end_lon": float(lon[i_last]) if ok[i_last] else None,
        "start": t0,
        "end": t1,
        "days": round(days, 1),
        "max_depth_m": round(float(ds.DEPTH.max()), 1),
        # unique count, not max: PROFILE numbering has gaps. One value per
        # up- or down-cast.
        "n_profiles": int(np.unique(ds.PROFILE.values[np.isfinite(ds.PROFILE.values)]).size)
        if "PROFILE" in ds else None,
        "temp_min": round(float(ds.TEMP.min()), 2),
        "temp_max": round(float(ds.TEMP.max()), 2),
        # decimated track for a quick path preview in the popup (~200 pts)
        "track": [
            [round(float(a), 4), round(float(b), 4)]
            for a, b in zip(lat[ok][:: max(1, ok.sum() // 200)],
                            lon[ok][:: max(1, ok.sum() // 200)])
        ],
        "file": path.name,
    }
    ds.close()
    return rec


def main() -> None:
    files = sorted(VIZ_DIR.glob("*_viz.nc"))
    if not files:
        raise SystemExit(f"No *_viz.nc files in {VIZ_DIR}")
    records = []
    for f in files:
        print(f"  {f.name}")
        records.append(summarise(f))
    OUT.write_text("const DEPLOYMENTS = " + json.dumps(records, indent=1) + ";\n")
    print(f"Wrote {len(records)} deployments -> {OUT.name}")


if __name__ == "__main__":
    main()
