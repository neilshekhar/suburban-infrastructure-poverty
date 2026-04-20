# Project Conventions

These conventions capture non-obvious project decisions so future contributors and AI assistants do not accidentally reverse them.

- Keep Git lightweight: commit notebooks, docs, and dependency files only.
- Keep local data and generated exports in Mediaflux, not GitHub.
- Do not commit `data/`, `outputs/`, GeoPackages, shapefiles, GeoJSON, CSV, Kepler HTML, or Kepler `*_config.json` exports.
- Commit notebooks without saved cell outputs so local absolute paths and large data previews are not published.
- Treat `notebooks/infra_map.ipynb` as the active end-to-end workflow.
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
