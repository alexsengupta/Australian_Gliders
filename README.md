# Australian Gliders

An interactive web app for exploring Australia's IMOS/ANFOG ocean-glider
archive: a clustered map of every deployment, and a per-deployment dashboard
with trajectory, depth–time sections, depth profiles, and a temperature–salinity
diagram — with temperature compared against a marine-heatwave climatology.

The app is a **static website** (one HTML file plus small pre-computed data
files). All heavy processing happens offline in a batch pipeline; the browser
only reads the results. No database, no application server.

> Full technical and deployment details are in
> **`Australian_Gliders_briefing.docx`**.

---

## Quick start

```bash
git clone https://github.com/alexsengupta/Australian_Gliders.git
cd Australian_Gliders

conda env create -f environment.yml      # one-time
conda activate gliders

# build a small scoped dataset to test end-to-end (~280 MB)
./run_pipeline.sh --match Forster

# serve and open
python -m http.server 8000               # http://localhost:8000/glider_map.html
```

To build the **whole** national archive (~30 GiB), first check the size, then
run the pipeline unscoped:

```bash
python fetch_all_anfog.py --inventory    # count + total size, no download
./run_pipeline.sh                        # download + clean + index + plot data
```

---

## How it works

The pipeline (`run_pipeline.sh`) chains four steps:

| Step | Script | Output |
|---|---|---|
| 1. Download | `fetch_all_anfog.py` | `anfog_data/<dep>/*.nc` (raw, resumable) |
| 2. Clean & shrink | `make_viz_subset.py` | `anfog_data_viz/*.nc` (QC-masked, float32, +density, ~5× smaller) |
| 3. Index | `extract_deployments.py` | `deployments.js` (one record per deployment) |
| 4. Plot data | `make_plotdata.py` | `plotdata/<id>_plot.js` (track + binned sections) |

The app (`glider_map.html`) loads `deployments.js` and `climatology.js` on
start, and lazily loads a deployment's `plotdata/*.js` only when its dashboard
is opened. It pulls Leaflet, Leaflet.markercluster, and Plotly from public CDNs.

`climatology.js` is a small **input** (NSW temperature climatology, four seasons
× marine-heatwave/non-heatwave), converted from Amandine's
`glider_mean_profile_TEMP_NSW.nc`. It is committed to the repo and regenerated
only when the baseline itself changes.

---

## Repository layout

```
fetch_all_anfog.py        download the full archive (both fleets)
get_anfog.py              sample downloader (three Forster missions)
make_viz_subset.py        QC-mask, select variables, add density, compress
extract_deployments.py    build the map index (deployments.js)
make_plotdata.py          build per-deployment plot data
run_pipeline.sh           chains the four steps (first / full build)
sync_reduced.py           incremental update: reduced-aware, deletes raw
glider_map.html           the app
climatology.js            NSW temperature climatology (input)
environment.yml           conda environment "gliders"
assets/                   glider photos (add locally; see the README there)
from Amandine/            climatology source NetCDF + notebook
README_run_notebook.md    how to run Amandine's Jupyter notebook
Australian_Gliders_briefing.docx   full briefing & deployment guide
```

Raw NetCDF, the cleaned subsets, `plotdata/`, and `deployments.js` are **not**
committed (see `.gitignore`) — they are rebuilt by the pipeline and published to
Nectar object storage.

---

## Deployment (Nectar)

Two pieces: a **public object-storage container** that serves the static app and
the small derived files (the website), and a **small cron VM** that runs the
update on a schedule and uploads the results into the container. The public site
has no server to maintain.

**Nectar does not keep the raw data.** The reduced subsets (`anfog_data_viz/`,
~5× smaller than raw) are the only bulky thing that persists there. Incremental
updates use `sync_reduced.py`, which decides what to fetch from the reduced set,
downloads each new deployment's raw NetCDF, subsets it, then **deletes the raw**.

Do the **first full build locally**, then copy the website files to the container
and `anfog_data_viz/` to the VM volume — you never copy raw NetCDF. Step-by-step
instructions (with the exact copy commands), a `publish.sh` example, and the
crontab entry are in the briefing document.

---

## Caveats

- The visualisation subsets, plot data, and T–S are **for viewing, not
  quantitative analysis** — QC is baked in, data is binned and decimated. Do
  science on the raw NetCDF.
- The climatology is **NSW-wide, temperature-only, valid to ~100 m**. Regional
  (and eventually monthly) climatologies are the main scientific upgrade.
- ANFOG's deep (~1000 m) Seaglider record **ends in 2018**; recent subsurface
  questions below the shelf need complementary data (Argo, moorings).

---

## Credits & data

Data: [IMOS](https://imos.org.au) Australian National Facility for Ocean Gliders
(ANFOG), via the [Australian Ocean Data Network](https://portal.aodn.org.au).
Climatology by Amandine. Glider photos: see `assets/README_glider_images.md`.

## Licence

_Add a licence before making the repository public (MIT is a common choice for
code; note that the IMOS data has its own attribution terms)._
