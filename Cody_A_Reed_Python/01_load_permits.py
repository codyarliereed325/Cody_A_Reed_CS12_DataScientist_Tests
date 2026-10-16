"""DDOT CS-12 Data Scientist assessment: Python test (Cody Arlie Reed).

Goal: enrich 2026 Public Space Occupancy Permit locations for DC Water,
PEPCO, and Washington Gas with the FHWA functional class of the road at
each location, plus the highest functional class for each permit.

Script 1 of the numbered scripts (run them in order):
    1. Load the occupancy permits from DDOT's ArcGIS REST service w/ SQL syntax.
    2. Keep only the three utilities, with one SQL query per utility.

Writes: data/utility_permit_locations_2026.csv.gz

Run from a terminal, from any folder:
    python 01_load_permits.py          (Windows: py 01_load_permits.py)
"""

import pandas as pd
import requests

from here import here

# ---------------------------------------------------------------------------
# Define global objects
# ---------------------------------------------------------------------------

# DDOT Public Space Occupancy Permits (ArcGIS REST layer 24) from the PDF.
OCCUPANCY_URL = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/"
                 "DCGIS_APPS/DDOT_TOPS/MapServer/24")

# SELECT: setting the fields to keep from layer 24
OCCUPANCY_SELECT = (
    "TrackingNumber, PermitNumber, LocationID, ApplicantCompany, "
    "EventTypeDescription, Status, ApplicationDate, IssueDate, "
    "WorkLocationFullAddress"
)

# WHERE: setting the query to all 2026 permits (applied for or issued) and
# only the two requested permit types
OCCUPANCY_WHERE = (
    "(EXTRACT(YEAR FROM ApplicationDate) = 2026 "
    "OR EXTRACT(YEAR FROM IssueDate) = 2026) "
    "AND EventTypeDescription IN "
    "('Construction Staging Area', 'Mobile Crane Work Zone')"
)

# WHERE, per utility: setting each utility to the ApplicantCompany values it
# applies under (found with a GROUP BY on ApplicantCompany). Only the three
# utilities named in the PDF; telecom and cable companies (e.g. Comcast,
# Verizon) also file these permits but are left out
UTILITY_WHERE = {
    "DC Water": "ApplicantCompany IN ('DCWater/CIP', 'DCWater/OPS', 'DCWater')",
    "PEPCO": "ApplicantCompany IN ('Potomac Electric Power Company', 'Pepco')",
    "Washington Gas": "ApplicantCompany = 'Wash Gas & Light Co.'",
}

# ORDER BY: setting each permit's locations to stay together
OCCUPANCY_ORDER_BY = "TrackingNumber, LocationID"

# ---------------------------------------------------------------------------
# Step 1: load the occupancy permit data
# ---------------------------------------------------------------------------

def load_occupancy_permits(where):
    """Upload the occupancy permit data in accordance with the instructions."""
    params = {
        "outFields": OCCUPANCY_SELECT,
        "where": where,
        "orderByFields": OCCUPANCY_ORDER_BY,
        "resultRecordCount": 2000,    # max records per request (according to the webpage)
        "f": "json",
    }

    rows = []
    while True:
        params["resultOffset"] = len(rows)
        response = requests.get(f"{OCCUPANCY_URL}/query",
                                params=params,
                                timeout=60)
        response.raise_for_status()
        page = response.json()
        if "error" in page:  # ArcGIS returns query errors in the JSON body
            raise RuntimeError(page["error"])

        for feature in page["features"]:
            # extract permit information and coordinates
            row = feature["attributes"]
            row["geometry_x"] = feature["geometry"]["x"]
            row["geometry_y"] = feature["geometry"]["y"]
            rows.append(row)

        # The server flags when more records remain
        if not page.get("exceededTransferLimit"):
            break

    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Step 2: keep only the three utilities (DC Water, PEPCO, and Washington Gas)
# ---------------------------------------------------------------------------

def load_utility_permits():
    """Run one query per utility and label each record with its utility."""
    frames = []
    for utility, utility_where in UTILITY_WHERE.items():
        # Each loop loads utility-specific data for 2026
        frame = load_occupancy_permits(f"({OCCUPANCY_WHERE}) AND ({utility_where})")
        frame["Utility"] = utility
        # Merge each frame
        frames.append(frame)
    return pd.concat(frames,
                     ignore_index=True)

# Load the 2026 permit locations for the three utilities
permits = load_utility_permits()

# Look at the data
permits.info()

# As of October 16, 2026: 5,038 permit locations and 12 variables
#   TrackingNumber           permit application ID; may have several locations
#   PermitNumber             assigned when the permit is issued (2,455 rows); renewals
#                            reuse the original number plus -R1, -R2, ...
#   LocationID               location within the application
#   ApplicantCompany         company that applied; identifies the utility
#   EventTypeDescription     permit type (all Construction Staging Area)
#   Status                   e.g. ISSUED, EXPIRED, APPROVED, NOTPAID
#   ApplicationDate          date applied, in milliseconds since 1970
#   IssueDate                date issued, in milliseconds since 1970; blank for
#                            applications not issued (e.g. APPROVED pending payment,
#                            NOTPAID, under review), which is why it is float64
#   WorkLocationFullAddress  block or address of the work location
#   geometry_x               x coordinate
#   geometry_y               y coordinate
#   Utility                  DC Water, PEPCO, or Washington Gas (set in step 2)

# Save the permit data as a compressed CSV
here("data").mkdir(exist_ok=True) # Create folder if it doesn't exist
permits.to_csv(here("data",
                    "utility_permit_locations_2026.csv.gz"),
               index=False)
