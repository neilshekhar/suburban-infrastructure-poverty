# Suburban Infrastructure Poverty

Suburban Infrastructure Poverty is an MDAP / Suburban Futures project at the University of Melbourne that maps infrastructure poverty across Greater Melbourne. The project combines recent population growth with public infrastructure locations to identify suburbs where services and facilities may not be keeping pace with growth.

## Data Sources

The analysis uses Australian Bureau of Statistics estimated resident population data to 2024 and Vicmap Features of Interest infrastructure data. The local data files used by the notebook, including `population.gpkg`, `melbourne.gpkg`, Vicmap shapefiles, and generated Kepler deliverables, are stored in the project Mediaflux collection

## Repository Contents

This GitHub repo contains only lightweight, reproducible project files:

- `notebooks/infra_map.ipynb`: the active end-to-end analysis notebook.
- `README.md`, `CONVENTIONS.md`, `requirements.txt`, and `.gitignore`: project documentation and setup files.

The repo should not include local data, processed GeoPackages, exported GeoJSON/CSV files, Kepler HTML files, or Kepler `map*.json` exports. Those files live in Mediaflux and are ignored by Git.

Notebook files are committed without saved cell outputs. This keeps GitHub lightweight and prevents local absolute paths or large data previews from being published.

## Setup

This project was developed with Python 3.11.6.

Create and activate a virtual environment from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If you use VS Code or Jupyter, select the `.venv` kernel before running the notebook.

If you rerun the notebook before committing, clear outputs again while keeping code cells intact:

```bash
jupyter nbconvert --clear-output --inplace notebooks/infra_map.ipynb
```

## How To Run

Open `notebooks/infra_map.ipynb`. In the first configuration cell, edit `POPULATION_PATH` and `INFRA_PATH` so they point to the local Mediaflux copies of `population.gpkg` and `FOI_POINT.shp`. Then run all cells from top to bottom.

## Outputs

The working notebook produces five export files for downstream mapping and review:

- `kepler_population_growth.geojson`: Map A polygon layer with SA2 population growth and facility count metrics.
- `kepler_infrastructure_points.geojson`: Map A point layer with infrastructure facilities categorized for Kepler.gl.
- `kepler_population_timeseries.geojson`: Map B polygon layer with annual population snapshots for the time animation.
- `kepler_infrastructure_timeseries.geojson`: Map B point layer with infrastructure facility timestamps aligned to the animation window.
- `infrastructure_poverty_summary.csv`: Tabular summary of population growth, facility counts, and facility-density metrics by SA2.

Export files are stored in Mediaflux, not GitHub.

Kepler map deliverables are also stored in Mediaflux, including HTML exports and `map*.json` configuration exports such as `map_a_config.json` and `map_b_config.json`.

## Map A vs Map B

Map A is the current-period (i.e 2024) infrastructure poverty view. It uses 2021-baseline population growth metrics and current infrastructure counts to show where Greater Melbourne suburbs have added people without a comparable level of facilities and services.

Map B is the time-series view. It uses a 2010 baseline to animate population growth and infrastructure availability through 2024, making it easier to see whether service provision has kept pace over time.

## Contributors

- Neil Shekhar
- Amanda Belton
- Emily Fitzgerald
