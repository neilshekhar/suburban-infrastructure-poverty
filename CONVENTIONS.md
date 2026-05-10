# Project Conventions

These conventions capture non-obvious project decisions so future contributors and AI assistants do not accidentally reverse them.

- Keep Git lightweight: commit notebooks, scripts, docs, and dependency files only.
- Keep local data and generated exports in Mediaflux, not GitHub.
- Do not commit `data/`, `outputs/`, GeoPackages, shapefiles, GeoJSON, CSV, Kepler HTML, or Kepler `*_config.json` exports.
- Commit notebooks without saved cell outputs so local absolute paths and large data previews are not published.
- Treat `notebooks/infra_map.ipynb` as the active end-to-end workflow.
- Treat `notebooks/self_employed_business_density.ipynb` as the active workflow for the self-employed business density map.
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
- The self-employed business density workflow uses ABS CABEE annualised `a` sheets only; do not use CABEE `b` sheets, which are experimental point-in-time sheets.
- The self-employed business density workflow drops CABEE `Industry Code == "X"` because those rows are currently unknown state-level dumps that should not be attributed to individual SA2s.
- The self-employed business density workflow covers 2019-2024, using CABEE releases `2017-2021`, `2018-2022`, and `2021-2025`.
- The self-employed business density workflow stops at 2024 because the ERP age/sex population source currently ends at 2024.
- The self-employed business density workflow uses non-employing businesses as the numerator and working-age residents aged 15-64 as the denominator.
- The self-employed business density workflow uses a working-age population floor of `500`; rows below the floor remain in the CSV for audit but are excluded from both map views.
- The self-employed business density workflow flags seven CBD/Southbank/industrial-estate SA2s separately instead of deleting them from the output.
- The default self-employed business map view is All Melbourne (incl. CBD); Residential Melbourne is available via the toggle and excludes the seven flagged central/distortion SA2s while still applying the population floor.
- Per-1,000 and change metrics are set to missing where working-age population is zero, avoiding `inf` values in downstream CSV/HTML outputs.
- The industry-filter table includes an `ALL` aggregate plus 19 ANZSIC division filters; the `ALL` rows must match `self_employed_business_density.csv` exactly.
- The Plotly HTML uses two figures inside one scaffold so both views retain independent year-slider and Play/Pause animation state.
- Industry-filter data is stored in one compact JavaScript payload and updates the active trace with `Plotly.react()` instead of preloading all industry/year/view trace combinations.
- The Plotly HTML inlines Plotly.js, but the Carto/OpenStreetMap basemap tiles still require internet access at view time.
- `scripts/self_employed_business_insights.py` is a pandas-only helper that reads processed self-employed business tables and prints presentation numbers; it should not create map outputs.
