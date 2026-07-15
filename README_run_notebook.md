# Running Amandine's Jupyter notebook

`from Amandine/GliderMissionsDownload.ipynb` downloads and processes ANFOG
glider data. Here is how to run it from scratch if you have never used a
notebook.

## What a notebook is

A `.ipynb` file is a list of **cells**. A cell is either text or code. You run
one cell at a time; its output appears directly beneath it. You run a cell by
selecting it and pressing **Shift + Enter**. Cells share memory, so a variable
made in cell 3 is still there in cell 7 — which means **order matters**: run
top to bottom.

## One-time setup

You have `conda` already (it is what the handover uses). Open **Terminal** and
run, once:

```bash
cd "~/Dropbox/My AI/Amandine_Gliders"
conda env create -f environment.yml     # builds an isolated environment "gliders"
```

This takes a few minutes and installs everything the notebook needs, kept
separate from your `base` environment (the handover flagged that `base` may
have a broken botocore — this avoids touching it).

## Each time you want to work

```bash
cd "~/Dropbox/My AI/Amandine_Gliders"
conda activate gliders
jupyter lab
```

`jupyter lab` opens a tab in your browser. In the file list on the left, open
`from Amandine/GliderMissionsDownload.ipynb`. Then either:

- press **Shift + Enter** to run cells one at a time (recommended the first
  time, so you see what each does), or
- menu **Run → Run All Cells** to run everything.

To stop, close the browser tab and press **Ctrl + C** twice in the Terminal.

## What to expect from THIS notebook — read before running

It is a work in progress, not a clean top-to-bottom script. Specifically:

- **Cell 4 downloads every Forster delayed-mode mission** into
  `Forster_downloads2/`. That is hundreds of MB and takes a while. Fine, just
  know it is happening. It skips files already downloaded, so re-running is
  cheap.
- **Cells 8 and 9 are commented out** (every line starts with `#`), so they do
  nothing. They are drafts.
- **Cell 10 will fail as-is.** It uses a variable `ds_mean` (the climatology)
  that is only loaded inside the commented-out cells. Before running cell 10,
  add a line loading it, and fix the path to where the file actually is:

  ```python
  ds_mean = xr.open_dataset("from Amandine/glider_mean_profile_TEMP_NSW.nc")
  ```

  (the notebook points at `./GLIDERSubsurfacedata/...`, which you do not have.)
- **Cell 5 always prints "Saved 0 TEMP files"** — a cosmetic bug (a counter is
  never incremented). The files are still written correctly.

## If a cell shows an error

The red traceback names the problem on its last line. The two you are most
likely to hit: `ModuleNotFoundError` (a package is missing — you are probably
in the wrong environment; re-run `conda activate gliders`) and `NameError`
(you ran a cell out of order, or skipped one — run the earlier cells first).

## Simpler alternative

If you only want the climatology comparison and not the full download, you do
not need this notebook at all — the web app (`glider_map.html`) already does
the depth-time sections, profiles, and anomaly-vs-climatology interactively.
The notebook is mainly useful for (re)building the processed files in bulk.
