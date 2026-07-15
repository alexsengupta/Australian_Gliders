# Glider images for the map popups

The map popup shows a photo of the glider based on its vehicle type. Drop two
image files in this `assets/` folder and they appear automatically:

- `slocum.jpg`     — shelf Slocum gliders (all current NSW/Forster deployments)
- `seaglider.jpg`  — deep (~1000 m) Seagliders (needed once you go national)

If a file is missing the popup just hides the image, so nothing breaks.

## Yes — you need two images

The ANFOG fleet is two physically different vehicles:

- **Slocum** — ~2 m torpedo shape, shelf vehicle capped near 200 m. Every
  deployment in the archive since 2018 is a Slocum.
- **Seaglider** — larger, laminar-flow hull with swept wings, dives to ~1000 m.
  ANFOG's Seaglider deployments all pre-date 2018, but they are in the national
  archive, so a national map needs their picture too.

The app already tags each deployment `Slocum` or `Seaglider` (from the hull
code) and requests the matching file, so two images cover the whole fleet.

## Where to get properly-licensed images

- **Wikimedia Commons — "Category:Underwater gliders"**
  https://commons.wikimedia.org/wiki/Category:Underwater_gliders
  Has `Slocum underwater glider.jpg` (4636×3076) and Seaglider photos. Check the
  licence on each file page (usually CC BY or CC BY-SA — keep the attribution).
- **IMOS / ANFOG** (Australian fleet, best match for this project):
  https://imos.org.au/facility/ocean-gliders — request or credit their photos.
- **Manufacturers** (for reference/permission): Teledyne Webb Research (Slocum),
  and the Seaglider line (now Huntington Ingalls / formerly Kongsberg).

Rename whatever you choose to `slocum.jpg` / `seaglider.jpg` and place here.
Landscape crops around 400×200 px look best; larger is fine (the popup crops).
