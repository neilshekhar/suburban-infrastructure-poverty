#!/usr/bin/env python3
"""Insight numbers for self-employed business density.

Run from the repository root:

    python scripts/self_employed_business_insights.py

The script intentionally uses only the Python standard library and pandas.
If a processed SA2->council lookup exists it will use that; otherwise it
derives the lookup from the existing GeoPackage with a small internal WKB
parser so the analysis stays reproducible without adding GeoPandas here.
"""

from __future__ import annotations

import math
import sqlite3
import struct
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
AGGREGATE_PATH = PROCESSED_DIR / "self_employed_business_density.csv"
BY_INDUSTRY_PATH = PROCESSED_DIR / "self_employed_business_density_by_industry.csv"
LOOKUP_PATH = PROCESSED_DIR / "sa2_council_lookup.csv"
GPKG_PATH = PROCESSED_DIR / "melbourne.gpkg"
SUMMARY_OUTPUT = PROCESSED_DIR / "self_employed_business_insights_summary.csv"
RATES_OUTPUT = PROCESSED_DIR / "self_employed_business_density_rates.csv"


CORRIDOR_LGAS = ["Wyndham", "Melton", "Hume", "Whittlesea", "Casey", "Cardinia", "Mitchell"]
INNER_LGAS = ["Melbourne", "Yarra", "Port Phillip", "Stonnington", "Boroondara"]

# The current GeoPackage uses short LGA names. These aliases make the script
# robust to future lookup CSVs that use formal council names such as
# "City of Melbourne" instead of "Melbourne".
LGA_NAME_NORMALISATIONS = {
    "City of Melbourne": "Melbourne",
    "City of Yarra": "Yarra",
    "City of Port Phillip": "Port Phillip",
    "City of Stonnington": "Stonnington",
    "City of Boroondara": "Boroondara",
    "City of Wyndham": "Wyndham",
    "City of Melton": "Melton",
    "City of Hume": "Hume",
    "City of Whittlesea": "Whittlesea",
    "City of Casey": "Casey",
    "Shire of Cardinia": "Cardinia",
    "Mitchell Shire": "Mitchell",
}


ANZSIC_DIVISIONS = {
    "A": "Agriculture, Forestry and Fishing",
    "B": "Mining",
    "C": "Manufacturing",
    "D": "Electricity, Gas, Water and Waste Services",
    "E": "Construction",
    "F": "Wholesale Trade",
    "G": "Retail Trade",
    "H": "Accommodation and Food Services",
    "I": "Transport, Postal and Warehousing",
    "J": "Information Media and Telecommunications",
    "K": "Financial and Insurance Services",
    "L": "Rental, Hiring and Real Estate Services",
    "M": "Professional, Scientific and Technical Services",
    "N": "Administrative and Support Services",
    "O": "Public Administration and Safety",
    "P": "Education and Training",
    "Q": "Health Care and Social Assistance",
    "R": "Arts and Recreation Services",
    "S": "Other Services",
}


START_YEAR = 2019
LATEST_YEAR = 2024

SELECTED_INDUSTRIES = ["I", "E", "M", "L"]
RATE_VIEWS = {
    "Residential": "include_in_primary_view",
    "All": "include_in_alternate_view",
}


def pct(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return math.nan
    return numerator / denominator * 100


def fmt_int(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{int(round(value)):,}"


def fmt_float(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:,.{digits}f}"


def fmt_pct(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:,.{digits}f}%"


def industry_label(code: str) -> str:
    if code == "ALL":
        return "All self-employed (aggregate)"
    return f"{code} - {ANZSIC_DIVISIONS.get(code, code)}"


def print_header(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


def read_required_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, **kwargs)


def normalise_council_name(name: str) -> str:
    name = str(name).strip()
    return LGA_NAME_NORMALISATIONS.get(name, name)


def gpkg_wkb_offset(blob: bytes) -> int:
    if blob[:2] != b"GP":
        raise ValueError("GeoPackage geometry blob does not start with GP magic bytes")
    flags = blob[3]
    envelope_code = (flags >> 1) & 7
    envelope_lengths = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    if envelope_code not in envelope_lengths:
        raise ValueError(f"Unsupported GeoPackage envelope code: {envelope_code}")
    return 8 + envelope_lengths[envelope_code]


class WKBReader:
    def __init__(self, blob: bytes):
        self.blob = blob

    def read_u32(self, offset: int, endian: str) -> tuple[int, int]:
        return struct.unpack(endian + "I", self.blob[offset : offset + 4])[0], offset + 4

    def read_f64(self, offset: int, endian: str) -> tuple[float, int]:
        return struct.unpack(endian + "d", self.blob[offset : offset + 8])[0], offset + 8

    def parse_geometry(self, offset: int) -> tuple[list[list[list[tuple[float, float]]]], int]:
        byte_order = self.blob[offset]
        endian = "<" if byte_order == 1 else ">"
        offset += 1
        geom_type, offset = self.read_u32(offset, endian)
        geom_type = geom_type % 1000
        if geom_type == 3:
            polygon, offset = self.parse_polygon_body(offset, endian)
            return [polygon], offset
        if geom_type == 6:
            polygon_count, offset = self.read_u32(offset, endian)
            polygons = []
            for _ in range(polygon_count):
                child_polygons, offset = self.parse_geometry(offset)
                polygons.extend(child_polygons)
            return polygons, offset
        raise ValueError(f"Unsupported WKB geometry type: {geom_type}")

    def parse_polygon_body(self, offset: int, endian: str) -> tuple[list[list[tuple[float, float]]], int]:
        ring_count, offset = self.read_u32(offset, endian)
        rings = []
        for _ in range(ring_count):
            point_count, offset = self.read_u32(offset, endian)
            ring = []
            for _ in range(point_count):
                x, offset = self.read_f64(offset, endian)
                y, offset = self.read_f64(offset, endian)
                ring.append((x, y))
            rings.append(ring)
        return rings, offset


def parse_gpkg_geometry(blob: bytes) -> list[list[list[tuple[float, float]]]]:
    reader = WKBReader(blob)
    polygons, _ = reader.parse_geometry(gpkg_wkb_offset(blob))
    return polygons


def ring_area_and_centroid(ring: list[tuple[float, float]]) -> tuple[float, float, float]:
    area_twice = 0.0
    cx_sum = 0.0
    cy_sum = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        area_twice += cross
        cx_sum += (x1 + x2) * cross
        cy_sum += (y1 + y2) * cross
    area = area_twice / 2.0
    if area == 0:
        return 0.0, math.nan, math.nan
    return area, cx_sum / (6.0 * area), cy_sum / (6.0 * area)


def geometry_centroid(polygons: list[list[list[tuple[float, float]]]]) -> tuple[float, float]:
    total_area = 0.0
    cx_total = 0.0
    cy_total = 0.0
    fallback_points = []
    for polygon in polygons:
        for ring in polygon:
            fallback_points.extend(ring)
            area, cx, cy = ring_area_and_centroid(ring)
            if area and not pd.isna(cx):
                total_area += area
                cx_total += cx * area
                cy_total += cy * area
    if total_area:
        return cx_total / total_area, cy_total / total_area
    xs = [p[0] for p in fallback_points]
    ys = [p[1] for p in fallback_points]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def point_in_ring(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y):
            x_intersect = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_intersect:
                inside = not inside
    return inside


def point_in_polygon(point: tuple[float, float], polygon: list[list[tuple[float, float]]]) -> bool:
    if not polygon or not point_in_ring(point, polygon[0]):
        return False
    return not any(point_in_ring(point, hole) for hole in polygon[1:])


def geometry_bounds(polygons: list[list[list[tuple[float, float]]]]) -> tuple[float, float, float, float]:
    xs = []
    ys = []
    for polygon in polygons:
        for ring in polygon:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def point_in_geometry(point: tuple[float, float], polygons: list[list[list[tuple[float, float]]]]) -> bool:
    return any(point_in_polygon(point, polygon) for polygon in polygons)


def derive_lookup_from_gpkg() -> tuple[pd.DataFrame, str]:
    if not GPKG_PATH.exists():
        raise FileNotFoundError(f"No SA2 council lookup CSV and missing GeoPackage fallback: {GPKG_PATH}")

    with sqlite3.connect(GPKG_PATH) as con:
        sa2_rows = con.execute(
            """
            select SA2_CODE_2021, SA2_NAME_2021, geom
            from greater_melb_sa2
            """
        ).fetchall()
        lga_rows = con.execute(
            """
            select LGA_NAME_2025, geom
            from greater_melb_local_gov_2025_any_intersect
            """
        ).fetchall()

    lgas = []
    for council, geom_blob in lga_rows:
        geometry = parse_gpkg_geometry(geom_blob)
        lgas.append(
            {
                "council": normalise_council_name(council),
                "geometry": geometry,
                "bounds": geometry_bounds(geometry),
            }
        )

    lookup_rows = []
    for sa2_code, sa2_name, geom_blob in sa2_rows:
        point = geometry_centroid(parse_gpkg_geometry(geom_blob))
        matched_council = None
        for lga in lgas:
            min_x, min_y, max_x, max_y = lga["bounds"]
            if not (min_x <= point[0] <= max_x and min_y <= point[1] <= max_y):
                continue
            if point_in_geometry(point, lga["geometry"]):
                matched_council = lga["council"]
                break
        lookup_rows.append(
            {
                "sa2_code": str(sa2_code),
                "sa2_name_lookup": sa2_name,
                "council": matched_council if matched_council is not None else "Unknown",
            }
        )

    return pd.DataFrame(lookup_rows), f"derived from {GPKG_PATH.relative_to(REPO_ROOT)} using SA2 centroids"


def load_sa2_council_lookup() -> tuple[pd.DataFrame, str]:
    if LOOKUP_PATH.exists():
        lookup = pd.read_csv(LOOKUP_PATH, dtype=str)
        rename_map = {}
        if "SA2_CODE_2021" in lookup.columns:
            rename_map["SA2_CODE_2021"] = "sa2_code"
        if "LGA_NAME_2025" in lookup.columns:
            rename_map["LGA_NAME_2025"] = "council"
        lookup = lookup.rename(columns=rename_map)
        if not {"sa2_code", "council"}.issubset(lookup.columns):
            raise ValueError(f"{LOOKUP_PATH} must contain sa2_code/council or SA2_CODE_2021/LGA_NAME_2025")
        lookup = lookup[["sa2_code", "council"]].copy()
        lookup["sa2_code"] = lookup["sa2_code"].astype(str)
        lookup["council"] = lookup["council"].map(normalise_council_name)
        return lookup, f"read from {LOOKUP_PATH.relative_to(REPO_ROOT)}"
    return derive_lookup_from_gpkg()


def attach_council(frame: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    out = frame.merge(lookup[["sa2_code", "council"]], on="sa2_code", how="left")
    out["council"] = out["council"].fillna("Unknown").map(normalise_council_name)
    return out


def assign_cluster(council: str, middle_lgas: set[str]) -> str:
    if council in CORRIDOR_LGAS:
        return "corridor"
    if council in INNER_LGAS:
        return "inner"
    if council in middle_lgas:
        return "middle"
    return "unknown"


def top_industries_for_cluster(industry_latest: pd.DataFrame, cluster: str, total: float, n: int = 5) -> pd.DataFrame:
    grouped = (
        industry_latest[
            industry_latest["cluster"].eq(cluster) & industry_latest["industry_division"].ne("ALL")
        ]
        .groupby("industry_division", as_index=False)["non_employing_count"]
        .sum()
    )
    grouped["share_pct"] = grouped["non_employing_count"].apply(lambda value: pct(value, total))
    grouped["industry"] = grouped["industry_division"].map(industry_label)
    return grouped.sort_values("share_pct", ascending=False).head(n)


def top_sa2_by_density(frame: pd.DataFrame, industry_code: str, cluster: str, year: int = LATEST_YEAR, n: int = 10) -> pd.DataFrame:
    return (
        frame[
            frame["year"].eq(year)
            & frame["industry_division"].eq(industry_code)
            & frame["cluster"].eq(cluster)
        ]
        .sort_values(
            ["non_employing_per_1000_working_age", "non_employing_count", "sa2_name"],
            ascending=[False, False, True],
        )
        .head(n)
        .copy()
    )


def print_sa2_table(frame: pd.DataFrame, include_working_age: bool = True) -> None:
    if frame.empty:
        print("No matching SA2s.")
        return
    for rank, row in enumerate(frame.itertuples(index=False), 1):
        if include_working_age:
            print(
                f"{rank:>2}. {row.sa2_name:<42} {row.council:<22} "
                f"count={fmt_int(row.non_employing_count):>6}  "
                f"working_age={fmt_int(row.working_age_pop):>7}  "
                f"density={fmt_float(row.non_employing_per_1000_working_age):>6}"
            )
        else:
            print(
                f"{rank:>2}. {row.sa2_name:<42} {row.council:<22} "
                f"count={fmt_int(row.non_employing_count):>6}  "
                f"density={fmt_float(row.non_employing_per_1000_working_age):>6}"
            )


def yoy_table(frame: pd.DataFrame, industry_code: str, cluster: str | None = None) -> pd.DataFrame:
    filtered = frame[frame["industry_division"].eq(industry_code)]
    if cluster is not None:
        filtered = filtered[filtered["cluster"].eq(cluster)]
    totals = filtered.groupby("year", as_index=False)["non_employing_count"].sum()
    totals["yoy_pct"] = totals["non_employing_count"].pct_change() * 100
    return totals


def count_for(frame: pd.DataFrame, year: int, industry_code: str, cluster: str | None = None) -> int:
    filtered = frame[frame["year"].eq(year) & frame["industry_division"].eq(industry_code)]
    if cluster is not None:
        filtered = filtered[filtered["cluster"].eq(cluster)]
    return int(filtered["non_employing_count"].sum())


def total_for_cluster(industry_frame: pd.DataFrame, cluster: str, year: int = LATEST_YEAR) -> int:
    return count_for(industry_frame, year, "ALL", cluster=cluster)


def write_melbourne_rate_table(industry_frame: pd.DataFrame) -> pd.DataFrame:
    industry_order = ["ALL"] + list(ANZSIC_DIVISIONS)
    rows = []
    for industry in industry_order:
        for view, include_col in RATE_VIEWS.items():
            for year in range(START_YEAR, LATEST_YEAR + 1):
                eligible = industry_frame[
                    industry_frame["industry_division"].eq(industry)
                    & industry_frame["year"].eq(year)
                    & industry_frame[include_col]
                ]
                working_age_pop = eligible["working_age_pop"].dropna().sum()
                business_count = eligible["non_employing_count"].dropna().sum()
                rows.append(
                    {
                        "industry": industry,
                        "view": view,
                        "year": year,
                        "melbourne_rate": (
                            float(business_count) / float(working_age_pop) * 1000 if working_age_pop else math.nan
                        ),
                    }
                )
    rates = pd.DataFrame(rows, columns=["industry", "view", "year", "melbourne_rate"])
    rates.to_csv(RATES_OUTPUT, index=False)
    return rates


def main() -> None:
    aggregate = read_required_csv(AGGREGATE_PATH, dtype={"sa2_code": str})
    by_industry = read_required_csv(BY_INDUSTRY_PATH, dtype={"sa2_code": str})

    lookup, lookup_source = load_sa2_council_lookup()
    aggregate = attach_council(aggregate, lookup)
    by_industry = attach_council(by_industry, lookup)
    melbourne_rate_table = write_melbourne_rate_table(by_industry)

    aggregate_primary = aggregate[aggregate["include_in_primary_view"]].copy()
    industry_primary = by_industry[by_industry["include_in_primary_view"]].copy()

    present_lgas = sorted(aggregate_primary["council"].dropna().unique())
    missing_named_lgas = [lga for lga in CORRIDOR_LGAS + INNER_LGAS if lga not in present_lgas]
    middle_lgas = sorted(set(present_lgas) - set(CORRIDOR_LGAS) - set(INNER_LGAS) - {"Unknown"})

    aggregate_primary["cluster"] = aggregate_primary["council"].apply(lambda value: assign_cluster(value, set(middle_lgas)))
    industry_primary["cluster"] = industry_primary["council"].apply(lambda value: assign_cluster(value, set(middle_lgas)))

    normalised_seen = {
        raw: normalised
        for raw, normalised in LGA_NAME_NORMALISATIONS.items()
        if raw in set(lookup["council"])
    }
    unknown_sa2s = sorted(aggregate_primary.loc[aggregate_primary["cluster"].eq("unknown"), "sa2_name"].unique())
    middle_sa2s = sorted(aggregate_primary.loc[aggregate_primary["cluster"].eq("middle"), "sa2_name"].unique())

    summary_rows = []

    print("Self-Employed Business Density - Presentation Insights")
    print(f"Lookup source: {lookup_source}")
    print(f"Primary-view SA2s: {aggregate_primary['sa2_code'].nunique():,}")
    print(f"Primary-view LGAs: {len(present_lgas):,}")
    print(f"LGA name normalisations applied at runtime: {'none' if not normalised_seen else normalised_seen}")
    print(f"Configured corridor/inner LGAs missing from primary-view data: {'none' if not missing_named_lgas else ', '.join(missing_named_lgas)}")
    print(f"Melbourne rate table written: {RATES_OUTPUT.relative_to(REPO_ROOT)} ({len(melbourne_rate_table):,} rows)")

    print_header("Analysis 1 - Industry mix by LGA cluster, 2024")
    industry_latest = industry_primary[industry_primary["year"].eq(LATEST_YEAR)].copy()
    cluster_totals = {cluster: total_for_cluster(industry_primary, cluster, LATEST_YEAR) for cluster in ["corridor", "inner", "middle"]}
    for cluster in ["corridor", "inner", "middle"]:
        print(f"\n{cluster.title()} cluster total self-employed businesses: {fmt_int(cluster_totals[cluster])}")
        top5 = top_industries_for_cluster(industry_latest, cluster, cluster_totals[cluster])
        for row in top5.itertuples(index=False):
            print(
                f"  {row.industry:<55} "
                f"count={fmt_int(row.non_employing_count):>7}  share={fmt_pct(row.share_pct):>7}"
            )

    print("\nSelected industry shares by cluster:")
    print(f"{'Industry':<55} {'Corridor':>10} {'Inner':>10} {'Middle':>10}")
    for code in SELECTED_INDUSTRIES:
        values = []
        for cluster in ["corridor", "inner", "middle"]:
            count = count_for(industry_primary, LATEST_YEAR, code, cluster=cluster)
            values.append(fmt_pct(pct(count, cluster_totals[cluster])))
        print(f"{industry_label(code):<55} {values[0]:>10} {values[1]:>10} {values[2]:>10}")
    corridor_transport_share = pct(count_for(industry_primary, LATEST_YEAR, "I", "corridor"), cluster_totals["corridor"])
    inner_prof_share = pct(count_for(industry_primary, LATEST_YEAR, "M", "inner"), cluster_totals["inner"])
    print(
        "Interpretation: Corridor self-employment is dominated by Transport-PSW "
        f"({fmt_pct(corridor_transport_share)}), while the inner cluster's biggest signal is "
        f"Professional Services ({fmt_pct(inner_prof_share)})."
    )
    summary_rows.append(
        {
            "analysis": "1",
            "label": "corridor_transport_share_2024_pct",
            "value": round(corridor_transport_share, 2),
            "headline": f"Transport-PSW is {fmt_pct(corridor_transport_share)} of corridor self-employed businesses in 2024.",
        }
    )

    print_header("Analysis 2 - Transport-PSW SA2 league table, corridors only, 2024")
    transport_top10 = top_sa2_by_density(industry_primary, "I", "corridor")
    print_sa2_table(transport_top10, include_working_age=True)
    top_transport = transport_top10.iloc[0]
    print(
        "Interpretation: The highest Transport-PSW densities are concentrated in outer growth-corridor SA2s, "
        f"led by {top_transport['sa2_name']} at {fmt_float(top_transport['non_employing_per_1000_working_age'])} per 1,000."
    )
    summary_rows.append(
        {
            "analysis": "2",
            "label": "top_corridor_transport_sa2_density_2024",
            "value": round(float(top_transport["non_employing_per_1000_working_age"]), 2),
            "headline": f"{top_transport['sa2_name']} leads corridor Transport-PSW density in 2024.",
        }
    )

    print_header("Analysis 3 - Transport-PSW year-by-year growth, metro vs corridors")
    metro_yoy = yoy_table(industry_primary, "I").rename(
        columns={"non_employing_count": "metro_count", "yoy_pct": "metro_yoy_pct"}
    )
    corridor_yoy = yoy_table(industry_primary, "I", "corridor").rename(
        columns={"non_employing_count": "corridor_count", "yoy_pct": "corridor_yoy_pct"}
    )
    growth = metro_yoy.merge(corridor_yoy, on="year")
    print(f"{'Year':<6} {'Metro count':>12} {'Metro YoY':>11} {'Corridor count':>16} {'Corridor YoY':>13}")
    for row in growth.itertuples(index=False):
        print(
            f"{row.year:<6} {fmt_int(row.metro_count):>12} {fmt_pct(row.metro_yoy_pct):>11} "
            f"{fmt_int(row.corridor_count):>16} {fmt_pct(row.corridor_yoy_pct):>13}"
        )
    metro_2019 = count_for(industry_primary, 2019, "I")
    metro_2021 = count_for(industry_primary, 2021, "I")
    metro_latest = count_for(industry_primary, LATEST_YEAR, "I")
    corridor_2019 = count_for(industry_primary, 2019, "I", "corridor")
    corridor_2021 = count_for(industry_primary, 2021, "I", "corridor")
    corridor_latest = count_for(industry_primary, LATEST_YEAR, "I", "corridor")
    metro_early_share = pct(metro_2021 - metro_2019, metro_latest - metro_2019)
    corridor_early_share = pct(corridor_2021 - corridor_2019, corridor_latest - corridor_2019)
    structural = metro_early_share < 50 and corridor_early_share < 50
    print(
        "Interpretation: Growth is "
        f"{'distributed across the full window (structural)' if structural else 'heavily concentrated around 2020-21'}; "
        f"2019-2021 accounts for {fmt_pct(metro_early_share)} of metro growth and "
        f"{fmt_pct(corridor_early_share)} of corridor growth."
    )
    summary_rows.append(
        {
            "analysis": "3",
            "label": "transport_growth_pattern",
            "value": round(metro_early_share, 2),
            "headline": f"2019-2021 accounts for {fmt_pct(metro_early_share)} of 2019-2024 metro Transport-PSW growth.",
        }
    )

    print_header("Analysis 4 - Construction comparison, corridors only, 2024")
    construction_top10 = top_sa2_by_density(industry_primary, "E", "corridor")
    print_sa2_table(construction_top10, include_working_age=True)
    overlap = sorted(set(transport_top10["sa2_code"]).intersection(set(construction_top10["sa2_code"])))
    overlap_names = sorted(transport_top10[transport_top10["sa2_code"].isin(overlap)]["sa2_name"].unique())
    print(f"\nOverlap with Transport-PSW top 10: {len(overlap)} SA2s")
    print(f"Overlapping SA2s: {'none' if not overlap_names else ', '.join(overlap_names)}")
    print(
        "Interpretation: Construction overlaps partly with Transport-PSW, but the overlap count shows these are related "
        "outer-corridor signals rather than identical SA2 rankings."
    )
    summary_rows.append(
        {
            "analysis": "4",
            "label": "transport_construction_top10_overlap",
            "value": len(overlap),
            "headline": f"{len(overlap)} SA2s appear in both corridor Transport-PSW and Construction top 10 lists.",
        }
    )

    print_header("Analysis 5 - Inner-suburb top SA2s for Professional Services, 2024")
    professional_top10 = top_sa2_by_density(industry_primary, "M", "inner")
    print_sa2_table(professional_top10, include_working_age=False)
    top_prof = professional_top10.iloc[0]
    print(
        "Interpretation: Professional Services density is an inner-suburb pattern, "
        f"led by {top_prof['sa2_name']} at {fmt_float(top_prof['non_employing_per_1000_working_age'])} per 1,000."
    )
    summary_rows.append(
        {
            "analysis": "5",
            "label": "top_inner_professional_services_sa2_density_2024",
            "value": round(float(top_prof["non_employing_per_1000_working_age"]), 2),
            "headline": f"{top_prof['sa2_name']} leads inner Professional Services density in 2024.",
        }
    )

    print_header("Analysis 6 - Corridor share of Greater Melbourne Transport-PSW growth")
    metro_i_2019 = count_for(industry_primary, 2019, "I")
    metro_i_latest = count_for(industry_primary, LATEST_YEAR, "I")
    corridor_i_2019 = count_for(industry_primary, 2019, "I", "corridor")
    corridor_i_latest = count_for(industry_primary, LATEST_YEAR, "I", "corridor")
    metro_increase = metro_i_latest - metro_i_2019
    corridor_increase = corridor_i_latest - corridor_i_2019
    corridor_growth_share = pct(corridor_increase, metro_increase)
    print(f"Greater Melbourne Transport-PSW count: 2019={fmt_int(metro_i_2019)}, {LATEST_YEAR}={fmt_int(metro_i_latest)}, increase={fmt_int(metro_increase)}")
    print(f"Corridor LGA Transport-PSW count:     2019={fmt_int(corridor_i_2019)}, {LATEST_YEAR}={fmt_int(corridor_i_latest)}, increase={fmt_int(corridor_increase)}")
    print(f"Corridor share of metro increase:     {fmt_pct(corridor_growth_share)}")
    print(
        "Interpretation: This is the headline number - corridor LGAs captured "
        f"{fmt_pct(corridor_growth_share)} of Greater Melbourne's Transport-PSW self-employed growth."
    )
    summary_rows.append(
        {
            "analysis": "6",
            "label": "corridor_share_of_metro_transport_growth_pct",
            "value": round(corridor_growth_share, 2),
            "headline": f"Corridor LGAs captured {fmt_pct(corridor_growth_share)} of metro Transport-PSW growth from 2019 to 2024.",
        }
    )

    print_header("Analysis 7 - Rental/Real Estate concentration check for inner suburbs, 2024")
    inner_l_count = count_for(industry_primary, LATEST_YEAR, "L", "inner")
    inner_all_count = count_for(industry_primary, LATEST_YEAR, "ALL", "inner")
    metro_l_count = count_for(industry_primary, LATEST_YEAR, "L")
    metro_all_count = count_for(industry_primary, LATEST_YEAR, "ALL")
    inner_l_share = pct(inner_l_count, inner_all_count)
    metro_l_share = pct(metro_l_count, metro_all_count)
    inner_to_metro_ratio = inner_l_share / metro_l_share if metro_l_share else math.nan
    print(f"Inner-LGA Rental/Real Estate share:        {fmt_pct(inner_l_share)} ({fmt_int(inner_l_count)} of {fmt_int(inner_all_count)})")
    print(f"Greater Melbourne Rental/Real Estate share:{fmt_pct(metro_l_share)} ({fmt_int(metro_l_count)} of {fmt_int(metro_all_count)})")
    print(f"Inner-to-metro share ratio:                {fmt_float(inner_to_metro_ratio, 2)}x")
    print(
        "Interpretation: Rental/Real Estate is genuinely concentrated in the inner cluster, "
        f"with an inner share {fmt_float(inner_to_metro_ratio, 2)} times the metro-wide share."
    )
    summary_rows.append(
        {
            "analysis": "7",
            "label": "inner_rental_real_estate_vs_metro_ratio",
            "value": round(inner_to_metro_ratio, 3),
            "headline": f"Inner Rental/Real Estate share is {fmt_float(inner_to_metro_ratio, 2)}x the metro-wide share.",
        }
    )

    print_header("Cluster coverage and middle-group audit")
    print(f"Corridor LGAs: {', '.join(CORRIDOR_LGAS)}")
    print(f"Inner LGAs:    {', '.join(INNER_LGAS)}")
    print(f"Middle LGAs:   {', '.join(middle_lgas)}")
    print(f"Middle SA2 count: {len(middle_sa2s):,}")
    print("Middle SA2s outside corridor and inner lists:")
    for name in middle_sa2s:
        council = aggregate_primary.loc[aggregate_primary["sa2_name"].eq(name), "council"].iloc[0]
        print(f"  - {name} ({council})")
    if unknown_sa2s:
        print("Unknown-cluster SA2s:")
        for name in unknown_sa2s:
            print(f"  - {name}")
    else:
        print("Unknown-cluster SA2s: none")

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    print()
    print(f"Summary CSV written: {SUMMARY_OUTPUT.relative_to(REPO_ROOT)} ({SUMMARY_OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
