# Suburban Infrastructure Poverty

Suburban Infrastructure Poverty is an MDAP / Suburban Futures project at the University of Melbourne that maps infrastructure poverty and related suburban change patterns across Greater Melbourne. The project currently includes infrastructure-poverty maps built from population growth and public facility locations, plus a self-employed business density map showing where Melbourne's non-employing business economy is concentrated and changing over time.

## Data Sources

The infrastructure-poverty workflow uses Australian Bureau of Statistics estimated resident population data to 2024 and Vicmap Features of Interest infrastructure data. The self-employed business workflow uses ABS Counts of Australian Businesses, including Entries and Exits (CABEE) SA2-by-industry-by-employment-size releases and ABS Estimated Resident Population by age and sex.

The local data files used by the notebooks, including `population.gpkg`, `melbourne.gpkg`, Vicmap shapefiles, CABEE Excel workbooks, ERP age/sex Excel workbooks, and generated map deliverables, are stored in the project Mediaflux collection.

## Repository Contents

This GitHub repo contains only lightweight, reproducible project files:

- `notebooks/infra_map.ipynb`: the active end-to-end infrastructure-poverty workflow.
- `notebooks/self_employed_business_density.ipynb`: the active workflow for the self-employed business density map.
- `scripts/self_employed_business_insights.py`: pandas-only helper script for presentation headline numbers from the processed self-employed business tables.
- `README.md`, `CONVENTIONS.md`, `requirements.txt`, and `.gitignore`: project documentation and setup files.

The repo should not include local data, processed GeoPackages, exported GeoJSON/CSV files, Kepler HTML files, Plotly HTML files, preview PNG files, or Kepler `*_config.json` exports. Those files live in Mediaflux and are ignored by Git.

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

If you rerun notebooks before committing, clear outputs again while keeping code cells intact:

```bash
jupyter nbconvert --clear-output --inplace notebooks/infra_map.ipynb notebooks/self_employed_business_density.ipynb
```

## How To Run

### Infrastructure Poverty

Open `notebooks/infra_map.ipynb`. In the first configuration cell, edit `POPULATION_PATH` and `INFRA_PATH` so they point to the local Mediaflux copies of `population.gpkg` and `FOI_POINT.shp`. Then run all cells from top to bottom.

### Self-Employed Business Density

Open `notebooks/self_employed_business_density.ipynb`. The notebook has three main sections: source-file inspection, analysis-table build, and map-output build. Confirm the CABEE Excel workbooks, ERP age/sex workbook, and `melbourne.gpkg` are available in the expected local `data/` paths from Mediaflux, then run the relevant cells from top to bottom.

To print the self-employed business presentation insight numbers from the processed tables, run:

```bash
python scripts/self_employed_business_insights.py
```

## Outputs

`notebooks/infra_map.ipynb` produces five export files for downstream mapping and review:

- `kepler_population_growth.geojson`: Current Infrastructure Poverty polygon layer with SA2 population growth and facility count metrics using facilities created by `2024-12-31`.
- `kepler_infrastructure_points.geojson`: Current Infrastructure Poverty point layer with infrastructure facilities categorized for Kepler.gl and created by `2024-12-31`.
- `kepler_population_timeseries.geojson`: Infrastructure Poverty Timeline polygon layer with annual population snapshots for the time animation.
- `kepler_infrastructure_timeseries.geojson`: Infrastructure Poverty Timeline point layer with infrastructure facility timestamps aligned to the animation window.
- `infrastructure_poverty_summary.csv`: Tabular summary of population growth, facility counts, and facility-density metrics by SA2.

Export files are stored in Mediaflux, not GitHub.

Kepler map deliverables are also stored in Mediaflux, including HTML exports such as `current_infrastructure_poverty.html` and `infrastructure_poverty_timeline.html`, and their paired configuration exports `current_infrastructure_poverty_config.json` and `infrastructure_poverty_timeline_config.json`.

The self-employed business workflow produces these local deliverables:

- `self_employed_business_density.csv`: tidy SA2-year table for 2019-2024 with non-employing businesses, working-age population, per-1,000 metrics, change since 2019, and view-inclusion flags.
- `self_employed_business_density_by_industry.csv`: industry-preserved SA2-year table used by the interactive industry filter.
- `self_employed_business_density_rates.csv`: industry-view-year Greater Melbourne average rates written by `scripts/self_employed_business_insights.py`; the notebook builds the same lookup in memory for tooltip comparisons.
- `self_employed_business_insights_summary.csv`: compact summary table of presentation headline numbers written by `scripts/self_employed_business_insights.py`.
- `self_employed_business_density.html`: interactive Plotly map with industry filtering, suburb/area search, Residential Melbourne and All Melbourne views, year sliders, Play/Pause animation controls, footer attribution, and a five-step Story Mode walkthrough.
- `self_employed_business_density_2024_preview.png`: static 2024 preview image for slides or review.

These self-employed business data and map outputs are stored in Mediaflux, not GitHub.

## Current Infrastructure Poverty vs Infrastructure Poverty Timeline

Current Infrastructure Poverty is the current-period (2024) view. It uses 2021-baseline population growth metrics, 2024 population, and facilities created on or before `2024-12-31` to show where Greater Melbourne suburbs have added people without a comparable level of facilities and services.

Infrastructure Poverty Timeline is the time-series view. It uses a 2010 baseline to animate population growth and infrastructure availability through 2024, making it easier to see whether service provision has kept pace over time. Timeline polygon counts are annual `June 30` snapshots, while point facilities animate by their actual creation dates; therefore the 2024 timeline polygon tooltip may differ slightly from the full-year Current Infrastructure Poverty snapshot.

## Self-Employed Business Density

Self-Employed Business Density maps non-employing businesses per 1,000 working-age residents by SA2 from 2019 to 2024, using working-age population aged 15-64 as the denominator. The workflow stops at 2024 because the ERP age/sex population source currently ends at 2024. The default map view is All Melbourne, including the CBD and flagged central/distortion SA2s. Residential Melbourne keeps the same working-age population floor but excludes these seven SA2s for suburb-to-suburb residential comparison: Melbourne CBD - East, Melbourne CBD - North, Melbourne CBD - West, Docklands, Southbank - East, Southbank (West) - South Wharf, and Port Melbourne Industrial.

The interactive HTML includes an industry filter, suburb/area search locator, year controls, comparison tooltips, footer attribution with ABS source links, and a Story Mode walkthrough. Tooltips compare each SA2 with the density-weighted Greater Melbourne average for the same industry, view, and year, not a simple mean across SA2s. Tooltip trend text shows both percent change and absolute per-1,000 change since 2019, while the bottom block keeps the raw business count, working-age residents, local per-1,000 rate, and Greater Melbourne average rate visible for auditability.

Story Mode has five curated steps: CBD/inner vs middle-ring vs growth-corridor economies, the CBD/inner knowledge-work cluster, the middle-ring business base, the outer-corridor Transport-Postal-Warehousing surge, and the distinct construction-corridor pattern. In Story Mode, central + inner means the CBD plus Melbourne, Yarra, Port Phillip, Stonnington and Boroondara LGAs; middle ring means established suburbs outside that inner cluster and outside the fringe-growth councils; growth corridors means Wyndham, Melton, Hume, Whittlesea, Casey, Cardinia and Mitchell. Story Mode pins the map to All Melbourne (incl. CBD) for all steps regardless of the user's previous view so CBD and inner-suburb patterns remain visible. Manually changing the view toggle, industry filter, or year slider exits Story Mode and returns the map to free exploration.

## Contributors
- Neil Shekhar
- Amanda Belton
- Emily Fitzgerald
