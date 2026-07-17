#!/usr/bin/env python3
"""Convert Amandine's combined regional climatology NetCDF into climatology.js.

Input : from Amandine/glider_mean_profile_regions_variables/glider_mean_profiles_mhw.nc
        dims (variable, region, condition, depth); vars mean_profile, std_profile.
Output: climatology.js  ->  window.CLIMATOLOGY = { depth, paper, regions:[...] }

Rerun this whenever Amandine ships an updated climatology. The app reads only
climatology.js; the source NetCDF does not need to be deployed.
"""

import json
from pathlib import Path

import numpy as np
import xarray as xr

HERE = Path(__file__).parent
SRC = HERE / "from Amandine" / "glider_mean_profile_regions_variables" / "glider_mean_profiles_mhw.nc"
OUT = HERE / "climatology.js"
PAPER = "https://egusphere.copernicus.org/preprints/2025/egusphere-2025-6045/"

# Official region boxes from the paper (lat = [south, north], lon = [west, east]).
BOUNDS = {
    "NSW": {"lat": [-36.7, -28.5], "lon": [149.7, 154.7]},
    "QLD": {"lat": [-19.7, -13.3], "lon": [144.7, 148.0]},
    "WAS": {"lat": [-33.5, -29.1], "lon": [113.2, 116.1]},
    "TAS": {"lat": [-44.6, -40.5], "lon": [146.8, 149.5]},
}


def clean(a):
    return [None if not np.isfinite(x) else round(float(x), 4) for x in a]


def main():
    c = xr.open_dataset(SRC)
    depth = [float(x) for x in c.depth.values]
    regions = []
    for ri, rg in enumerate(c.region.values):
        rg = str(rg)
        vars_ = {}
        for vi, v in enumerate(c.variable.values):
            v = str(v)
            mean, std = {}, {}
            for ci, cond in enumerate(c.condition.values):
                mean[str(cond)] = clean(c.mean_profile.values[vi, ri, ci])
                std[str(cond)] = clean(c.std_profile.values[vi, ri, ci])
            vars_[v] = {"mean": mean, "std": std}
        regions.append({"code": rg, "bounds": BOUNDS.get(rg), "vars": vars_})
    out = {"depth": depth, "paper": PAPER, "regions": regions}
    OUT.write_text("window.CLIMATOLOGY = " + json.dumps(out, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT.name}: {OUT.stat().st_size/1024:.1f} KB, "
          f"regions {[r['code'] for r in regions]}, vars {list(regions[0]['vars'])}")


if __name__ == "__main__":
    main()
