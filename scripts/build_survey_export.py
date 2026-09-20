"""Build the representative 62-row handheld export used in the assignment."""

from __future__ import annotations

import csv
from pathlib import Path

COLUMNS = [
    "asset_id",
    "name",
    "asset_type",
    "latitude",
    "longitude",
    "elevation_m",
    "surveyed_on",
    "surveyor",
    "status",
    "condition_score",
    "attribute_json",
]

# 52 accepted (some messy, cleaned by the pipeline) + 10 rejects ≈ 1/6.
ROWS: list[dict[str, str]] = [
    # Messy-but-valid: spaces, mixed case, compass letters, same surveyor typed differently.
    {"asset_id": "PL-0001", "name": "  NORTH   feeder pole ", "asset_type": "Pole", "latitude": "20.2961 N", "longitude": "85.8245 E", "elevation_m": "45.2", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "8", "attribute_json": '{"height_m": 9.1, "material": "concrete"}'},
    {"asset_id": "PL-0002", "name": "south ring  road pole", "asset_type": "POLE", "latitude": "20.2704", "longitude": "85.8401", "elevation_m": "42.0", "surveyed_on": "2026-09-10", "surveyor": "a patnaik", "status": "ACTIVE", "condition_score": "6", "attribute_json": '{"height_m": 8.5}'},
    {"asset_id": "PL-0003", "name": "Patia junction pole", "asset_type": "pole", "latitude": "20.3530", "longitude": "85.8238 E", "elevation_m": "", "surveyed_on": "2026-09-10", "surveyor": "A  PATNAIK", "status": "active", "condition_score": "4", "attribute_json": '{"height_m": 7.8}'},
    {"asset_id": "PL-0004", "name": "Nayapalli feeder pole", "asset_type": "pole", "latitude": "20.2845", "longitude": "85.8122", "elevation_m": "44.1", "surveyed_on": "2026-09-11", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "9", "attribute_json": '{"height_m": 10.0, "material": "steel"}'},
    {"asset_id": "PL-0005", "name": "Old town pole", "asset_type": "pole", "latitude": "20.2410", "longitude": "85.8340", "elevation_m": "38.6", "surveyed_on": "2026-09-11", "surveyor": "r k mishra", "status": "decommissioned", "condition_score": "1", "attribute_json": '{"height_m": 6.2}'},
    {"asset_id": "PL-0006", "name": "Chandrasekharpur pole", "asset_type": "pole", "latitude": "20.3301", "longitude": "85.8180", "elevation_m": "46.8", "surveyed_on": "2026-09-11", "surveyor": "S. Das", "status": "active", "condition_score": "7", "attribute_json": '{"height_m": 9.0}'},
    {"asset_id": "PL-0007", "name": "Khandagiri pole", "asset_type": "pole", "latitude": "20.2622", "longitude": "85.7785", "elevation_m": "51.3", "surveyed_on": "2026-09-12", "surveyor": "S. Das", "status": "proposed", "condition_score": "10", "attribute_json": '{"height_m": 11.0}'},
    {"asset_id": "PL-0008", "name": "Vani vihar pole", "asset_type": "pole", "latitude": "20.2920", "longitude": "85.8415", "elevation_m": "43.0", "surveyed_on": "2026-09-12", "surveyor": "B. Sahoo", "status": "active", "condition_score": "5", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0009", "name": "Saheed nagar pole", "asset_type": "pole", "latitude": "20.2888", "longitude": "85.8450", "elevation_m": "42.7", "surveyed_on": "2026-09-12", "surveyor": "B. Sahoo", "status": "active", "condition_score": "3", "attribute_json": '{"height_m": 7.5}'},
    {"asset_id": "PL-0010", "name": "Rasulgarh pole", "asset_type": "pole", "latitude": "20.2680", "longitude": "85.8620", "elevation_m": "40.2", "surveyed_on": "2026-09-12", "surveyor": "A. Patnaik", "status": "active", "condition_score": "8", "attribute_json": '{"height_m": 9.4}'},
    {"asset_id": "PL-0011", "name": "Cuttack road pole", "asset_type": "pole", "latitude": "20.3015", "longitude": "85.8555", "elevation_m": "41.9", "surveyed_on": "2026-09-13", "surveyor": "L. Jena", "status": "active", "condition_score": "6", "attribute_json": '{"height_m": 8.8}'},
    {"asset_id": "PL-0012", "name": "Airport approach pole", "asset_type": "pole", "latitude": "20.2540", "longitude": "85.8175", "elevation_m": "39.4", "surveyed_on": "2026-09-13", "surveyor": "L. Jena", "status": "active", "condition_score": "2", "attribute_json": '{"height_m": 7.0}'},
    {"asset_id": "PL-0013", "name": "Infocity pole", "asset_type": "pole", "latitude": "20.3408", "longitude": "85.8062", "elevation_m": "47.5", "surveyed_on": "2026-09-13", "surveyor": "S. Das", "status": "active", "condition_score": "9", "attribute_json": '{"height_m": 10.2}'},
    {"asset_id": "PL-0014", "name": "Jaydev vihar pole", "asset_type": "pole", "latitude": "20.3010", "longitude": "85.8190", "elevation_m": "44.8", "surveyed_on": "2026-09-13", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "7", "attribute_json": '{"height_m": 8.6}'},
    {"asset_id": "PL-0015", "name": "Unit 1 market pole", "asset_type": "pole", "latitude": "20.2708", "longitude": "85.8333", "elevation_m": "41.1", "surveyed_on": "2026-09-14", "surveyor": "B. Sahoo", "status": "active", "condition_score": "8", "attribute_json": '{"height_m": 9.0}'},
    {"asset_id": "PL-0016", "name": "Bapuji nagar pole", "asset_type": "pole", "latitude": "20.2655", "longitude": "85.8280", "elevation_m": "40.8", "surveyed_on": "2026-09-14", "surveyor": "A. Patnaik", "status": "active", "condition_score": "4", "attribute_json": '{"height_m": 7.9}'},
    {"asset_id": "PL-0017", "name": "Laxmisagar pole", "asset_type": "pole", "latitude": "20.2558", "longitude": "85.8488", "elevation_m": "39.0", "surveyed_on": "2026-09-14", "surveyor": "L. Jena", "status": "active", "condition_score": "5", "attribute_json": '{"height_m": 8.2}'},
    {"asset_id": "PL-0018", "name": "Bomikhal pole", "asset_type": "pole", "latitude": "20.2782", "longitude": "85.8584", "elevation_m": "41.6", "surveyed_on": "2026-09-14", "surveyor": "S. Das", "status": "active", "condition_score": "6", "attribute_json": '{"height_m": 8.4}'},
    {"asset_id": "PL-0019", "name": "Sundarpada pole", "asset_type": "pole", "latitude": "20.2388", "longitude": "85.8210", "elevation_m": "37.2", "surveyed_on": "2026-09-15", "surveyor": "R. K. Mishra", "status": "proposed", "condition_score": "10", "attribute_json": '{"height_m": 11.5}'},
    {"asset_id": "PL-0020", "name": "Ghatikia pole", "asset_type": "pole", "latitude": "20.2585", "longitude": "85.7704", "elevation_m": "52.1", "surveyed_on": "2026-09-15", "surveyor": "B. Sahoo", "status": "active", "condition_score": "7", "attribute_json": '{"height_m": 9.3}'},
    {"asset_id": "VL-0001", "name": "Master canteen valve", "asset_type": "valve", "latitude": "20.2689", "longitude": "85.8406", "elevation_m": "41.5", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "8", "attribute_json": '{"bore_mm": 150}'},
    {"asset_id": "VL-0002", "name": "  AG square   valve", "asset_type": "Valve", "latitude": "20.2755 N", "longitude": "85.8330", "elevation_m": "42.2", "surveyed_on": "2026-09-10", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "3", "attribute_json": '{"bore_mm": 100}'},
    {"asset_id": "VL-0003", "name": "Kalpana square valve", "asset_type": "VALVE", "latitude": "20.2496", "longitude": "85.8419", "elevation_m": "", "surveyed_on": "2026-09-11", "surveyor": "S. Das", "status": "active", "condition_score": "6", "attribute_json": '{"bore_mm": 200}'},
    {"asset_id": "VL-0004", "name": "Rajmahal valve", "asset_type": "valve", "latitude": "20.2712", "longitude": "85.8310", "elevation_m": "41.8", "surveyed_on": "2026-09-11", "surveyor": "L. Jena", "status": "decommissioned", "condition_score": "2", "attribute_json": '{"bore_mm": 80}'},
    {"asset_id": "VL-0005", "name": "CRP square valve", "asset_type": "valve", "latitude": "20.2968", "longitude": "85.8188", "elevation_m": "45.0", "surveyed_on": "2026-09-12", "surveyor": "B. Sahoo", "status": "active", "condition_score": "9", "attribute_json": '{"bore_mm": 250}'},
    {"asset_id": "VL-0006", "name": "Sainik school valve", "asset_type": "valve", "latitude": "20.3095", "longitude": "85.8312", "elevation_m": "44.4", "surveyed_on": "2026-09-12", "surveyor": "A. Patnaik", "status": "active", "condition_score": "5", "attribute_json": '{"bore_mm": 150}'},
    {"asset_id": "VL-0007", "name": "Nalco square valve", "asset_type": "valve", "latitude": "20.3220", "longitude": "85.8195", "elevation_m": "46.1", "surveyed_on": "2026-09-13", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "7", "attribute_json": '{"bore_mm": 300}'},
    {"asset_id": "VL-0008", "name": "Kalinga stadium valve", "asset_type": "valve", "latitude": "20.2914", "longitude": "85.8230", "elevation_m": "44.0", "surveyed_on": "2026-09-13", "surveyor": "S. Das", "status": "proposed", "condition_score": "10", "attribute_json": '{"bore_mm": 200}'},
    {"asset_id": "VL-0009", "name": "Delta square valve", "asset_type": "valve", "latitude": "20.2801", "longitude": "85.8377", "elevation_m": "42.6", "surveyed_on": "2026-09-14", "surveyor": "L. Jena", "status": "active", "condition_score": "4", "attribute_json": '{"bore_mm": 125}'},
    {"asset_id": "VL-0010", "name": "Fire station valve", "asset_type": "valve", "latitude": "20.2664", "longitude": "85.8448", "elevation_m": "41.0", "surveyed_on": "2026-09-15", "surveyor": "B. Sahoo", "status": "active", "condition_score": "8", "attribute_json": '{"bore_mm": 150}'},
    {"asset_id": "MH-0001", "name": "Janpath chamber", "asset_type": "manhole", "latitude": "20.2725", "longitude": "85.8362", "elevation_m": "41.7", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "6", "attribute_json": '{"depth_m": 2.4}'},
    {"asset_id": "MH-0002", "name": "  lewis  road  chamber", "asset_type": "Manhole", "latitude": "20.2502", "longitude": "85.8388", "elevation_m": "39.8", "surveyed_on": "2026-09-11", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "3", "attribute_json": '{"depth_m": 1.8}'},
    {"asset_id": "MH-0003", "name": "Forest park chamber", "asset_type": "MANHOLE", "latitude": "20.2633 N", "longitude": "85.8266 E", "elevation_m": "", "surveyed_on": "2026-09-11", "surveyor": "S. Das", "status": "active", "condition_score": "8", "attribute_json": '{"depth_m": 2.1}'},
    {"asset_id": "MH-0004", "name": "IRC village chamber", "asset_type": "manhole", "latitude": "20.3077", "longitude": "85.8125", "elevation_m": "45.6", "surveyed_on": "2026-09-12", "surveyor": "L. Jena", "status": "active", "condition_score": "7", "attribute_json": '{"depth_m": 2.6}'},
    {"asset_id": "MH-0005", "name": "Dumduma chamber", "asset_type": "manhole", "latitude": "20.2448", "longitude": "85.7902", "elevation_m": "48.0", "surveyed_on": "2026-09-12", "surveyor": "B. Sahoo", "status": "decommissioned", "condition_score": "0", "attribute_json": '{"depth_m": 1.5}'},
    {"asset_id": "MH-0006", "name": "Patrapada chamber", "asset_type": "manhole", "latitude": "20.2390", "longitude": "85.7755", "elevation_m": "50.4", "surveyed_on": "2026-09-13", "surveyor": "A. Patnaik", "status": "active", "condition_score": "5", "attribute_json": '{"depth_m": 2.0}'},
    {"asset_id": "MH-0007", "name": "Sailashree vihar chamber", "asset_type": "manhole", "latitude": "20.3355", "longitude": "85.8144", "elevation_m": "47.2", "surveyed_on": "2026-09-13", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "9", "attribute_json": '{"depth_m": 2.8}'},
    {"asset_id": "MH-0008", "name": "Niladri vihar chamber", "asset_type": "manhole", "latitude": "20.3488", "longitude": "85.8210", "elevation_m": "46.9", "surveyed_on": "2026-09-14", "surveyor": "S. Das", "status": "proposed", "condition_score": "10", "attribute_json": '{"depth_m": 3.0}'},
    {"asset_id": "MH-0009", "name": "Mancheswar chamber", "asset_type": "manhole", "latitude": "20.3102", "longitude": "85.8588", "elevation_m": "42.3", "surveyed_on": "2026-09-14", "surveyor": "L. Jena", "status": "active", "condition_score": "4", "attribute_json": '{"depth_m": 1.9}'},
    {"asset_id": "MH-0010", "name": "VSS nagar chamber", "asset_type": "manhole", "latitude": "20.2988", "longitude": "85.8495", "elevation_m": "43.1", "surveyed_on": "2026-09-15", "surveyor": "B. Sahoo", "status": "active", "condition_score": "6", "attribute_json": '{"depth_m": 2.2}'},
    {"asset_id": "TR-0001", "name": "Unit 4 transformer", "asset_type": "transformer", "latitude": "20.2766", "longitude": "85.8299", "elevation_m": "42.0", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "7", "attribute_json": '{"rating_kva": 250}'},
    {"asset_id": "TR-0002", "name": "  BJB  college  transformer", "asset_type": "Transformer", "latitude": "20.2618", "longitude": "85.8422", "elevation_m": "40.5", "surveyed_on": "2026-09-10", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "4", "attribute_json": '{"rating_kva": 100}'},
    {"asset_id": "TR-0003", "name": "KIIT transformer", "asset_type": "TRANSFORMER", "latitude": "20.3548 N", "longitude": "85.8194", "elevation_m": "48.2", "surveyed_on": "2026-09-11", "surveyor": "S. Das", "status": "active", "condition_score": "8", "attribute_json": '{"rating_kva": 500}'},
    {"asset_id": "TR-0004", "name": "AIIMS transformer", "asset_type": "transformer", "latitude": "20.2315", "longitude": "85.7888", "elevation_m": "49.6", "surveyed_on": "2026-09-11", "surveyor": "L. Jena", "status": "active", "condition_score": "9", "attribute_json": '{"rating_kva": 630}'},
    {"asset_id": "TR-0005", "name": "Baramunda transformer", "asset_type": "transformer", "latitude": "20.2684", "longitude": "85.8001", "elevation_m": "46.0", "surveyed_on": "2026-09-12", "surveyor": "B. Sahoo", "status": "decommissioned", "condition_score": "1", "attribute_json": '{"rating_kva": 63}'},
    {"asset_id": "TR-0006", "name": "Chandaka transformer", "asset_type": "transformer", "latitude": "20.3602", "longitude": "85.7908", "elevation_m": "", "surveyed_on": "2026-09-12", "surveyor": "A. Patnaik", "status": "active", "condition_score": "6", "attribute_json": '{"rating_kva": 315}'},
    {"asset_id": "TR-0007", "name": "Jatni feeder transformer", "asset_type": "transformer", "latitude": "20.1610", "longitude": "85.7075", "elevation_m": "55.4", "surveyed_on": "2026-09-13", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "5", "attribute_json": '{"rating_kva": 200}'},
    {"asset_id": "TR-0008", "name": "Nandankanan transformer", "asset_type": "transformer", "latitude": "20.4005", "longitude": "85.8218", "elevation_m": "44.7", "surveyed_on": "2026-09-13", "surveyor": "S. Das", "status": "proposed", "condition_score": "10", "attribute_json": '{"rating_kva": 400}'},
    {"asset_id": "TR-0009", "name": "Cuttack road transformer", "asset_type": "transformer", "latitude": "20.3058", "longitude": "85.8602", "elevation_m": "41.4", "surveyed_on": "2026-09-14", "surveyor": "L. Jena", "status": "active", "condition_score": "3", "attribute_json": '{"rating_kva": 160}'},
    {"asset_id": "TR-0010", "name": "Pahala transformer", "asset_type": "transformer", "latitude": "20.3255", "longitude": "85.8901", "elevation_m": "40.0", "surveyed_on": "2026-09-14", "surveyor": "B. Sahoo", "status": "active", "condition_score": "8", "attribute_json": '{"rating_kva": 250}'},
    {"asset_id": "TR-0011", "name": "Hanspal transformer", "asset_type": "transformer", "latitude": "20.3188", "longitude": "85.8720", "elevation_m": "40.9", "surveyed_on": "2026-09-15", "surveyor": "A. Patnaik", "status": "active", "condition_score": "7", "attribute_json": '{"rating_kva": 200}'},
    {"asset_id": "TR-0012", "name": "Sisupalgarh transformer", "asset_type": "transformer", "latitude": "20.2266", "longitude": "85.8544", "elevation_m": "38.8", "surveyed_on": "2026-09-15", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "2", "attribute_json": '{"rating_kva": 100}'},
    # Known reject faults (assignment 1.5), mixed into the export.
    {"asset_id": "PL-0001", "name": "Duplicate north feeder pole", "asset_type": "pole", "latitude": "20.2962", "longitude": "85.8246", "elevation_m": "45.0", "surveyed_on": "2026-09-16", "surveyor": "A. Patnaik", "status": "active", "condition_score": "8", "attribute_json": '{"height_m": 9.1}'},
    {"asset_id": "", "name": "Unmarked chamber near market", "asset_type": "manhole", "latitude": "20.2700", "longitude": "85.8400", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "S. Das", "status": "active", "condition_score": "5", "attribute_json": '{"depth_m": 2.0}'},
    {"asset_id": "pl-0142", "name": "Bad code format pole", "asset_type": "pole", "latitude": "20.2800", "longitude": "85.8300", "elevation_m": "42.0", "surveyed_on": "2026-09-10", "surveyor": "L. Jena", "status": "active", "condition_score": "6", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0099", "name": "Latitude out of range pole", "asset_type": "pole", "latitude": "95.0000", "longitude": "85.8245", "elevation_m": "40.0", "surveyed_on": "2026-09-10", "surveyor": "B. Sahoo", "status": "active", "condition_score": "7", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0098", "name": "Non numeric longitude pole", "asset_type": "pole", "latitude": "20.2900", "longitude": "east of temple", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "7", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0097", "name": "Overscored condition pole", "asset_type": "pole", "latitude": "20.2910", "longitude": "85.8250", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "R. K. Mishra", "status": "active", "condition_score": "14", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0096", "name": "Blank condition pole", "asset_type": "pole", "latitude": "20.2920", "longitude": "85.8260", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "S. Das", "status": "active", "condition_score": "", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0095", "name": "Future dated pole", "asset_type": "pole", "latitude": "20.2930", "longitude": "85.8270", "elevation_m": "41.0", "surveyed_on": "2027-03-01", "surveyor": "L. Jena", "status": "active", "condition_score": "8", "attribute_json": '{"height_m": 8.0}'},
    {"asset_id": "PL-0094", "name": "Broken json pole", "asset_type": "pole", "latitude": "20.2940", "longitude": "85.8280", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "B. Sahoo", "status": "active", "condition_score": "8", "attribute_json": "{height: 9"},
    {"asset_id": "PL-0093", "name": "Unknown type pump house", "asset_type": "pump", "latitude": "20.2950", "longitude": "85.8290", "elevation_m": "41.0", "surveyed_on": "2026-09-10", "surveyor": "A. Patnaik", "status": "active", "condition_score": "8", "attribute_json": '{"rating_kva": 50}'},
]


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "survey_export.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"Wrote {len(ROWS)} rows to {path}")


if __name__ == "__main__":
    main()
