"""DDOT CS-12 Data Scientist assessment: Python test (Cody Arlie Reed).

Script 2 of the numbered scripts (run them in order):
    3. Look up the nearest roadway for each unique permit coordinate with
       DDOT's linear referencing system (LRS) tool.
    4. Clean the roadway lookups.
    5. Attach the FHWA functional class from DDOT's Roadway SubBlock layer
       with a SQL query on SubBlockKey, and keep only roadways that have one
       (this filters out alleys).

Reads:  data/utility_permit_locations_2026.csv.gz  (from 01_load_permits.py)
Writes: data/lrs_roadways.csv.gz       (the LRS lookups, step 3)
        data/lrs_roadways_fhwa.csv.gz  (clean roadways ready to merge, step 5)

Run from a terminal, from any folder:
    python 02_lrs_roadways.py          (Windows: py 02_lrs_roadways.py)
"""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from here import here

# ---------------------------------------------------------------------------
# Define global objects
# ---------------------------------------------------------------------------

# DDOT linear referencing system (LRS) tool from the PDF: nearest roadway to a point
LRS_URL = ("https://rh.dcgis.dc.gov/dcgis/rest/services/DDOT/RoadwayBlocks/"
           "MapServer/exts/DdotLrsExtensions/getPointOnSubBlock")

# Setting how far the LRS looks for a roadway, in meters (required, 0 to 200)
LRS_SEARCH_RADIUS = 50

# Setting how many LRS requests run at once
LRS_WORKERS = 8

# Setting the column types used to reload the saved LRS lookups
ROADWAY_COLUMN_TYPES = {
    "geometry_x": "float64",
    "geometry_y": "float64",
    "LRSError": "str",
    "SubBlockKey": "str",
    "RouteName": "str",
    "RouteType": "str",
    "UnitBlock": "str",
    "DistanceMeters": "float64",
    "DCFunctionalClassCode": "Int64",    # blank for alleys and driveways (no class)
    "DCFunctionalClass": "str",
}

# DDOT Roadway SubBlock layer (ArcGIS REST layer 162) from the PDF
SUBBLOCK_URL = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/"
                "DCGIS_DATA/Transportation_WebMercator/MapServer/162")

# SELECT: setting the fields to keep from layer 162
SUBBLOCK_SELECT = "SUBBLOCKKEY, FHWAFUNCTIONALCLASS"

# Setting how many SubBlockKeys go in one query (longer URLs are refused)
SUBBLOCK_KEYS_PER_QUERY = 200

# FHWA functional class names, from the coded values on the layer 162 page
FHWA_CLASS_NAMES = {
    1: "Interstate",
    2: "Principal Arterial - Other Freeways or Expressways",
    3: "Principal Arterial - Other",
    4: "Minor Arterial",
    5: "Major Collector",
    6: "Minor Collector",
    7: "Local",
}

# ---------------------------------------------------------------------------
# Load the permit data and find the unique coordinates
# ---------------------------------------------------------------------------

# Load the permit locations saved by 01_load_permits.py
permits = pd.read_csv(here("data",
                           "utility_permit_locations_2026.csv.gz"))

# Gather unique coordinates
coords = permits[["geometry_x",
                  "geometry_y"]].drop_duplicates()

# ---------------------------------------------------------------------------
# Step 3: look up the nearest roadway for each unique coordinate (LRS)
# ---------------------------------------------------------------------------

def lookup_roadway(x, y):
    """Nearest roadway to one coordinate from the LRS tool."""
    params = {
        "x": x,
        "y": y,
        "inSR": 3857,                        # permit coordinates are Web Mercator
        "outSR": 3857,
        "searchRadius": LRS_SEARCH_RADIUS,
        "returnNearestMatchOnly": "true",    # only the closest roadway
        "f": "json",
    }

    # Keep the input coordinates so the results can be merged back to the permits
    row = {"geometry_x": x,
           "geometry_y": y,
           "LRSError": None}  # filled in only if the lookup fails
    try:
        response = requests.get(LRS_URL,
                                params=params,
                                timeout=60)
        response.raise_for_status()
        answer = response.json()
    except requests.RequestException as error:  # note the failure and keep going
        row["LRSError"] = str(error)
        return row
    if "error" in answer:  # the LRS also returns errors in the JSON body
        row["LRSError"] = answer["error"].get("message")
        return row

    for road in answer.get("pointOnSubBlocks", []):  # empty if no roadway is in range
        # extract roadway information and the DC functional class
        other = road.get("roadData",
                         {}).get("roadwayAttributes",
                                 {}).get("other", {})
        row["SubBlockKey"] = road.get("subBlockKey")
        row["RouteName"] = road.get("routeName")
        row["RouteType"] = road.get("routeType")
        row["UnitBlock"] = road.get("unitBlock")
        row["DistanceMeters"] = road.get("offsetInMeters")
        row["DCFunctionalClassCode"] = other.get("functionalClassCode")
        row["DCFunctionalClass"] = other.get("functionalClass")

    return row

def lookup_roadways(coordinates):
    """Run lookup_roadway for every coordinate, LRS_WORKERS requests at a time."""
    with ThreadPoolExecutor(max_workers=LRS_WORKERS) as pool:
        rows = list(pool.map(lookup_roadway,
                             coordinates["geometry_x"],
                             coordinates["geometry_y"]))
    return pd.DataFrame(rows)

# Nearest roadway for each unique coordinate
roadways = lookup_roadways(coords)

# Retry any lookups that failed (e.g. a brief network outage)
failed = roadways["LRSError"].notna()
roadways = pd.concat([roadways[~failed],
                      lookup_roadways(roadways[failed])],
                     ignore_index=True)

# Look at the data
roadways.info()

# Save the roadway lookups as a compressed CSV
roadways.to_csv(here("data",
                     "lrs_roadways.csv.gz"),
                index=False)

# ---------------------------------------------------------------------------
# Step 4: clean the roadway lookups
# ---------------------------------------------------------------------------

# Reload the saved lookups with explicit column types. Starting from the saved
# file also means the steps below can be rerun on their own, without repeating
# the lookups
roadways = pd.read_csv(here("data",
                            "lrs_roadways.csv.gz"),
                       dtype=ROADWAY_COLUMN_TYPES)

# Drop the LRSError column if there are no mentioned failures
if roadways["LRSError"].isna().all():
    roadways = roadways.drop(columns="LRSError")
else:
    print(f"{roadways['LRSError'].notna().sum():,} LRS lookups failed; "
          "rerun 02_lrs_roadways.py to retry them")

# Count each roadway type
route_type_counts = (roadways.groupby("RouteType")
                     .size()
                     .sort_values(ascending=False))
print(route_type_counts)

# Count each class type-functional code combination
class_code_count = (roadways.groupby(["DCFunctionalClassCode",
                                       "DCFunctionalClass"],
                                      dropna=False)  # keep the blank code (no class)
                     .size())
print(class_code_count)

# Count each roadway type-functional code combination
class_types_count = (roadways.groupby(["RouteType",
                                       "DCFunctionalClassCode"],
                                      dropna=False)  # keep the blank code (no class)
                     .size())
print(class_types_count)

# ---------------------------------------------------------------------------
# Step 5: attach the FHWA functional class (SQL on SubBlockKey) and filter
# out alleys
# ---------------------------------------------------------------------------

def load_subblocks(keys):
    """Look up the FHWA functional class for each SubBlockKey in layer 162."""
    rows = []
    for start in range(0, len(keys), SUBBLOCK_KEYS_PER_QUERY):
        batch = keys[start:start + SUBBLOCK_KEYS_PER_QUERY]
        params = {
            "outFields": SUBBLOCK_SELECT,
            "where": "SUBBLOCKKEY IN (" + ", ".join(f"'{key}'" for key in batch) + ")",
            "returnGeometry": "false",
            "f": "json",
        }
        response = requests.get(f"{SUBBLOCK_URL}/query",
                                params=params,
                                timeout=60)
        response.raise_for_status()
        page = response.json()
        if "error" in page:  # ArcGIS returns query errors in the JSON body
            raise RuntimeError(page["error"])

        for feature in page["features"]:
            # extract the key and its FHWA functional class
            rows.append({"SubBlockKey": feature["attributes"]["SUBBLOCKKEY"],
                         "FHWAFunctionalClassCode": feature["attributes"]["FHWAFUNCTIONALCLASS"]})

    return pd.DataFrame(rows).astype({"FHWAFunctionalClassCode": "Int64"})

# FHWA functional class for each roadway the LRS returned
subblocks = load_subblocks(roadways["SubBlockKey"].dropna().unique().tolist())
roadways = roadways.merge(subblocks,
                          on="SubBlockKey",
                          how="left")
roadways["FHWAFunctionalClass"] = roadways["FHWAFunctionalClassCode"].map(FHWA_CLASS_NAMES)

# Every alley lacks a functional class, and the few other roads without one
# (driveways, a walkway) are insignificant, so keep only roadways that are
# not alleys and have an FHWA functional code
has_class = ((roadways["RouteType"] != "Alley")
             & roadways["FHWAFunctionalClassCode"].notna())
roadways = roadways[has_class]

# Look at the data
roadways.info()

# Save the clean roadways, ready to merge with the permits, as a compressed CSV
roadways.to_csv(here("data",
                     "lrs_roadways_fhwa.csv.gz"),
                index=False)
