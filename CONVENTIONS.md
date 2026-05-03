# Project Conventions

These conventions capture non-obvious project decisions so future contributors and AI assistants do not accidentally reverse them.

- Keep Git lightweight: commit notebooks, docs, and dependency files only.
- Keep local data and generated exports in Mediaflux, not GitHub.
- Do not commit `data/`, `outputs/`, GeoPackages, shapefiles, GeoJSON, CSV, Kepler HTML, or Kepler `*_config.json` exports.
- Commit notebooks without saved cell outputs so local absolute paths and large data previews are not published.
- Treat `notebooks/infra_map.ipynb` as the active end-to-end workflow.
- Treat `notebooks/home_business_map.ipynb` as the active Map 3 workflow for home-based business density.
- Use GDA2020 (`EPSG:7844`) throughout the working spatial data.
- Use `EPSG:7855` only for centroid and buffering operations that require projected distances.
- Spatial clipping uses `gpd.clip()` against a dissolved Melbourne boundary, not spatial joins with `intersects`.
- Monuments are deliberately excluded from infrastructure categories.
- `CRDATE_PFI` dates before 2010 are unreliable Vicmap bulk-load artifacts.
- Current Infrastructure Poverty uses 2021-baseline metrics with 2024 population and facilities created on or before `2024-12-31`.
- Infrastructure Poverty Timeline uses a 2010 baseline.
- Infrastructure Poverty Timeline polygon counts are annual `June 30` snapshots, while point facilities animate by their actual creation dates.
- Infrastructure Poverty Timeline clamps pre-2010 facilities to `2010-01-01`.
- Infrastructure Poverty Timeline drops facilities created after `2024-12-31`.
- Working GeoDataFrames keep `snake_case` column names.
- Human-readable column names are applied at export only.
- Infrastructure category `child care` uses a space, not an underscore.
- Map 3 uses ABS CABEE annualised `a` sheets only; do not use CABEE `b` sheets, which are experimental point-in-time sheets.
- Map 3 drops CABEE `Industry Code == "X"` because those rows are currently unknown state-level dumps that should not be attributed to individual SA2s.
- Map 3 covers 2019-2025, using CABEE releases `2017-2021`, `2018-2022`, and `2021-2025`.
- Map 3 uses non-employing businesses as the numerator and working-age residents aged 15-64 as the denominator.
- Map 3 uses a working-age population floor of `500`; rows below the floor remain in the CSV for audit but are excluded from both map views.
- Map 3 flags seven CBD/Southbank/industrial-estate SA2s separately instead of deleting them from the output.
- Map 3's default Residential Melbourne view excludes the seven flagged central/distortion SA2s; the All Melbourne view includes them while still applying the population floor.
- Map 3 uses 2024 ERP age/sex population as the denominator for 2025 because the ERP source currently ends at 2024.
- Map 3 sets per-1,000 and change metrics to missing where working-age population is zero, avoiding `inf` values in downstream CSV/HTML outputs.
- Map 3 uses two Plotly figures inside one HTML scaffold so both views retain independent year-slider and Play/Pause animation state.
- Map 3 Plotly HTML inlines Plotly.js, but the Carto/OpenStreetMap basemap tiles still require internet access at view time.
