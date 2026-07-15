#!/usr/bin/env python3
"""Generate per-deployment plot data for the glider map app.

For each *_viz.nc, writes plotdata/<id>_plot.js containing:
  - track: decimated positions (~25k pts) with days-since-launch for colouring
  - sections: depth-time binned grids (median, 2 h x 2 m) for each variable

Loaded lazily by glider_map.html when the user opens the plot panel.
Rerun after adding deployments (after make_viz_subset.py + extract_deployments.py).
"""

import json
from pathlib import Path

import numpy as np
import xarray as xr

VIZ_DIR = Path(__file__).parent / "anfog_data_viz"
OUT_DIR = Path(__file__).parent / "plotdata"

MAX_TRACK_PTS = 25_000
TIME_BIN_H = 2.0
DEPTH_BIN_M = 2.0

# colorscale + whether higher values are "warmer"; profile axis direction
VARS = {
    "TEMP":   {"label": "Temperature", "units": "°C",        "cmap": "RdYlBu", "reverse": True},
    "PSAL":   {"label": "Salinity",    "units": "PSU",       "cmap": "Viridis", "reverse": False},
    "SIGMA0": {"label": "Density σ₀",  "units": "kg m⁻³",    "cmap": "Cividis", "reverse": False},
    "DOX2":   {"label": "Oxygen",      "units": "µmol kg⁻¹", "cmap": "YlGnBu", "reverse": False},
    "CPHL":   {"label": "Chlorophyll", "units": "mg m⁻³",    "cmap": "YlGn",   "reverse": False},
    "BBP":    {"label": "Backscatter", "units": "m⁻¹",       "cmap": "Turbid", "reverse": False},
    "CDOM":   {"label": "CDOM",        "units": "ppb",        "cmap": "Turbid", "reverse": False},
}


def r(x, nd=3):
    """Round, mapping NaN -> None for JSON."""
    return None if not np.isfinite(x) else round(float(x), nd)


def build(path: Path) -> dict:
    ds = xr.open_dataset(path)
    t = ds.TIME.values
    t0 = t[0]
    days = (t - t0) / np.timedelta64(1, "D")
    lat, lon = ds.LATITUDE.values, ds.LONGITUDE.values
    depth = ds.DEPTH.values

    # --- track: decimated, coloured by days since launch -------------------
    ok = np.isfinite(lat) & np.isfinite(lon)
    idx = np.flatnonzero(ok)[:: max(1, int(ok.sum() // MAX_TRACK_PTS))]
    track = {
        "lat": [round(float(v), 5) for v in lat[idx]],
        "lon": [round(float(v), 5) for v in lon[idx]],
        "days": [round(float(v), 3) for v in days[idx]],
        "step": int(max(1, ok.sum() // MAX_TRACK_PTS)),
        "start": np.datetime_as_string(t0, unit="m"),
    }

    # --- sections: median-binned depth-time grids --------------------------
    tb = np.arange(0, np.ceil(days[-1] * 24 / TIME_BIN_H) + 1) * TIME_BIN_H / 24
    dmax = np.nanmax(depth)
    db = np.arange(0, dmax + DEPTH_BIN_M, DEPTH_BIN_M)
    t_centres = [
        np.datetime_as_string(t0 + np.timedelta64(int(v * 86400), "s"), unit="m")
        for v in (tb[:-1] + tb[1:]) / 2
    ]
    d_centres = [float(v) for v in (db[:-1] + db[1:]) / 2]

    ti = np.clip(np.digitize(days, tb) - 1, 0, len(tb) - 2)
    di_ok = np.isfinite(depth)

    sections = {}
    for v, meta in VARS.items():
        if v not in ds:
            continue
        vals = ds[v].values
        g = np.isfinite(vals) & di_ok
        if g.sum() < 100:
            continue
        di = np.clip(np.digitize(depth[g], db) - 1, 0, len(db) - 2)
        flat = ti[g] * (len(db) - 1) + di
        order = np.argsort(flat)
        fs, vs = flat[order], vals[g][order]
        bounds = np.flatnonzero(np.diff(fs)) + 1
        cells = np.split(vs, bounds)
        ids = fs[np.concatenate(([0], bounds))]
        grid = np.full((len(tb) - 1) * (len(db) - 1), np.nan)
        grid[ids.astype(int)] = [np.median(c) for c in cells]
        grid = grid.reshape(len(tb) - 1, len(db) - 1)
        lo, hi = np.nanpercentile(grid, [2, 98])
        nd = 4 if v in ("BBP",) else 2  # backscatter is small-magnitude
        sections[v] = {
            **meta,
            "z": [[r(x, nd) for x in row] for row in grid.T],  # depth rows, time cols
            "zmin": r(lo, nd), "zmax": r(hi, nd),
        }

    ds.close()
    return {
        "id": path.stem.replace("_viz", ""),
        "track": track,
        "t": t_centres,
        "d": d_centres,
        "sections": sections,
    }


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for f in sorted(VIZ_DIR.glob("*_viz.nc")):
        data = build(f)
        out = OUT_DIR / f"{data['id']}_plot.js"
        payload = json.dumps(data, separators=(",", ":"))
        out.write_text(
            f'window.PLOTDATA = window.PLOTDATA || {{}};\n'
            f'window.PLOTDATA["{data["id"]}"] = {payload};\n'
        )
        print(f"  {out.name}: {out.stat().st_size/1e6:.2f} MB, "
              f"vars: {list(data['sections'])}")


if __name__ == "__main__":
    main()
