# Handover: IMOS ANFOG glider data

**Context for a fresh session.** Prior work was chat-only, no filesystem access. This
session should have the local machine.

---

## Goal

Get a working handle on IMOS glider data. Longer-term interest is subsurface
structure in the East Australian Current, including subsurface marine heatwaves.
Nothing has been analysed yet — we are still at the "understand the archive"
stage.

---

## Where things stand

### Working directory
`~/.../Amandine_Gliders/` (exact path to be confirmed)

### Files
- `get_anfog.py` — inventory / download / inspect script. Anonymous S3 via boto3.
  Three subcommands: `--inventory`, `--download`, `--inspect`.
- `check_AODN.py` — earlier scratch script, crashed on a pyarrow bug. Superseded.
- `anfog_data/` — created by `--download`. May or may not be populated yet.

### Immediate next step
Run, if not already done:
```bash
python get_anfog.py --download   # ~280 MB
python get_anfog.py --inspect
```
Then read the `--inspect` output. That is the first thing this session should look at.

---

## Environment — ONE KNOWN PROBLEM

Installing boto3 into `(base)` upgraded botocore to 1.43.45 and broke a pin:

```
aiobotocore 2.19.0 requires botocore<1.36.4,>=1.36.0
```

`aiobotocore` backs `s3fs`, which backs `dask` / `intake-esm`. The base env may now
be broken for unrelated CMIP6 work.

**Check first:**
```bash
conda activate base && python -c "import s3fs; print('ok')"
```
If it fails: `pip install "botocore<1.36.4"` in base, and move the glider work to a
dedicated env. This was flagged but not confirmed fixed.

---

## The archive, as established by direct inspection

Two buckets. Public, no credentials, `--no-sign-request` / `signature_version=UNSIGNED`.

| | Bucket | Contents | Size |
|---|---|---|---|
| NetCDF (canonical) | `s3://imos-data/IMOS/ANFOG/` | `REALTIME/`, `seaglider/`, `slocum_glider/` | 30.2 GiB, 7,606 objects |
| Parquet (derived) | `s3://aodn-cloud-optimised/slocum_glider_delayed_qc.parquet/` | Slocum delayed-mode only | 35.4 GiB, 570 objects |

THREDDS (`https://thredds.aodn.org.au/thredds/{dodsC,fileServer}/IMOS/ANFOG/...`)
serves the *same objects* as `imos-data`. Path structure mirrors the S3 prefix exactly.
`dodsC` = OPeNDAP (lazy, subsettable). `fileServer` = whole-file HTTP.

### Deployment folder structure
Naming: `<Site><YYYYMMDD>`, date = deployment start, **in local time**.

Each folder holds **exactly one NetCDF** (~97% of bytes) plus ~17 small files
(a `.kml` track and plots, ~3 MB). No gridded product. No FV00.

Filename decomposition:
```
IMOS_ANFOG_BCEOPSTUV_20240517T000650Z_SL287_FV01_timeseries_END-20240619T234913Z.nc
           │         │                │     │    │
           params    start (UTC)      hull  QC'd  flat 1-D series
```

---

## Three findings that reversed earlier assumptions

These were all corrections to things stated confidently and wrongly. Do not
re-derive them from priors.

**1. Parquet is LARGER than NetCDF, not smaller.**
35.4 GiB (Slocum delayed only) vs 30.2 GiB (everything). Parquet denormalises:
coordinates repeat per row, packed `int16` gets promoted to float, QC and
provenance columns are added. Columnar compression does not recover it. Parquet
still wins on *bytes transferred per subsetted query*, which is the number that
matters — but not on bytes at rest.

**2. There is no Seaglider Parquet.** The cloud-optimised bucket has Slocum only.

**3. The ANFOG Seaglider fleet appears DEAD.**
Last seaglider deployment: `Brisbane20180320`. Nothing after March 2018. 45
deployments total. Meanwhile Slocum runs to `TasEastCoast20260603` (last month).

This is the single most consequential fact in this handover. The Seagliders are
the ~1000 m vehicles; the Slocums are shelf vehicles capped near 200 m. So:

> **For anything recent and subsurface, ANFOG gliders may not be able to answer
> the question.** The deep record ends in 2018.

**Unresolved.** Did the fleet retire, move to another facility, or stall in
delayed-mode processing? Not established. Worth one email to the ANFOG node at
UWA, or check the ANFOG metadata record. Should be resolved *before* designing
any analysis.

---

## Gotchas, confirmed and suspected

**Confirmed — folder date vs file date can differ by one day.**
`Forster20250225/` contains a file starting `20250224T235115Z`. Folder name is
local (AEDT, UTC+11); file timestamp is UTC. Never build an exact-match join
between folder name and `time_coverage_start`. Tolerate ±1 day.

**Confirmed — deployment names are not cleanly parseable.**
At least four disambiguation conventions for same-site same-day deployments:
`JervisBay20180503a`, `MissionBeach0120220126`, `ScottReef120230424`,
`Perth20110626_1`, `Brisbane20180306A`, `ForsterA20210329`. A regex expecting
`^([A-Za-z]+)(\d{8})$` will silently drop these. Parse the trailing 8 digits as
date, treat the rest as an opaque label.

**Confirmed — pyarrow 19.0.0 crashes on the AODN Parquet.**
`ParquetException: Repetition level histogram size mismatch`, a hard C++ abort
(uncatchable in Python). Apache Arrow GH-45283, fixed in 19.0.1. Only relevant if
returning to the Parquet route.

**Suspected, needs checking in `--inspect` output:**
- Data is a flat 1-D timeseries, not (profile × depth). Building a depth-time
  section requires binning by yourself. The depth-bin choice is a real analysis
  decision, not a formatting one.
- QC flags: IMOS convention 1=good, 2=probably good, 3=probably bad, 4=bad,
  9=missing. Default filter should be `flag <= 2`.
- **Thermal lag on the conductivity cell** will produce spurious salinity spikes
  precisely at sharp thermoclines — i.e. exactly where the science is. Determine
  whether FV01 processing *corrects* this or merely *flags* it. Check variable
  attributes. This changes what PSAL can be used for.
- `BCEOPSTUV` param code: C/T/P/S/O and U/V are readable (conductivity,
  temperature, pressure, salinity, oxygen, currents). B and E are guesses
  (backscatter? irradiance/PAR?). The variable list settles it — do not trust
  the guess.

---

## Sanity checks worth knowing

Three Forster deployments, three *different* vehicles (SL287, SL210, SL995):

| Deployment | Vehicle | Days | Size | MB/day |
|---|---|---|---|---|
| Forster20240517 | SL287 | 34.0 | 122.6 MB | 3.61 |
| Forster20241030 | SL210 | 26.8 | 107.3 MB | 4.01 |
| Forster20250225 | SL995 | 12.2 |  50.5 MB | 4.13 |

Sampling config is stable across the fleet at ~3.6–4.1 MB/day, so file size is a
proxy for mission duration. Feb 2025 mission was short (12 d) — possibly an early
recovery, worth noting when assessing spatial coverage.

Note that repeat deployments at one site are **cross-vehicle** comparisons:
different sensor units, different calibration histories.

---

## Suggested order of work

1. Confirm base env is not broken.
2. Run `--download` and `--inspect`; read the QC flag histogram and variable list.
3. Resolve the B and E parameter codes from the actual file.
4. Determine FV01's thermal-lag handling from the variable attributes.
5. Plot one deployment as a depth-time section (requires binning) to see what a
   glider transect actually looks like.
6. **Then** revisit whether the Seaglider archive stopping in 2018 is fatal to the
   subsurface heatwave question, and if so, what the alternatives are (Argo,
   moorings, non-IMOS deep gliders).

Do not skip 6 just because 1–5 went smoothly. Format familiarity is not evidence
that the data can answer the science question.
