"""DDOT CS-12 Data Scientist assessment: Tableau test (Cody Arlie Reed).

Goal: the average business days to approve new Public Space Construction
Permits issued in fiscal year 2026 (FY26), with segments that show where
approval times are meaningfully different.

Data prep for the Tableau workbook:
    1. Load the construction permits from DDOT's ArcGIS REST service w/ SQL syntax.
    2. Keep one row per permit.
    3. Correct the time stamps and count the business days to approve.
    4. Group each permit's work types into a permit type category.

Writes: data/construction_permits_fy26.csv  (the workbook's data source)

Run from a terminal, from any folder:
    python prep/01_prepare_permits.py          (Windows: py prep\\01_prepare_permits.py)
"""

import re

import numpy as np
import pandas as pd
import requests

from here import here

# ---------------------------------------------------------------------------
# Define global objects
# ---------------------------------------------------------------------------

# DDOT Public Space Construction Permits (ArcGIS REST layer 23) from the PDF.
PERMITS_URL = ("https://maps2.dcgis.dc.gov/dcgis/rest/services/"
               "DCGIS_APPS/DDOT_TOPS/MapServer/23")

# SELECT: setting the fields to keep from layer 23
PERMITS_SELECT = (
    "TrackingNumber, ApplicantCompany, TypeDetailNames, EWRNumber, "
    "ApplicationDate, LastResubmissionRequestDate, LastApprovalDate, "
    "IssueDate, LastUpdateDate"
)

# WHERE: setting the query to the PDF's criteria
#   - only new permits (renewals have RenewalDescription = 'Renewal')
#   - applied for on or after October 1, 2025
#   - issued in FY26 (October 1, 2025 through September 30, 2026)
#   - approved, so the days to approve can be counted (drops 5 issued permits
#     that have no approval date)
# The time stamps run 4 hours ahead (see step 3), so midnight Eastern on
# October 1 is stored as 04:00
PERMITS_WHERE = (
    "RenewalDescription = 'New' "
    "AND ApplicationDate >= TIMESTAMP '2025-10-01 04:00:00' "
    "AND IssueDate >= TIMESTAMP '2025-10-01 04:00:00' "
    "AND IssueDate < TIMESTAMP '2026-10-01 04:00:00' "
    "AND LastApprovalDate IS NOT NULL"
)

# ORDER BY: setting each permit's locations to stay together, oldest update
# first (OBJECTID gives paging a fixed order)
PERMITS_ORDER_BY = "TrackingNumber, LastUpdateDate, OBJECTID"

# District of Columbia legal public holidays in FY26, from the Office of the
# City Administrator: https://edpm.dc.gov/issuances/legal-public-holidays/
# (December 24, 2025 was an early 2 PM closing, not a holiday)
DC_HOLIDAYS = {
    "2025-10-13": "Indigenous Peoples' Day",
    "2025-11-11": "Veterans Day",
    "2025-11-27": "Thanksgiving Day",
    "2025-12-25": "Christmas Day",
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Dr. Martin Luther King, Jr.'s Birthday",
    "2026-02-16": "Washington's Birthday",
    "2026-04-16": "DC Emancipation Day",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
}

# Setting the columns (and their order) for the Tableau data source
OUTPUT_COLUMNS = [
    "TrackingNumber", "ApplicantCompany", "PermitTypeCategory", "TypeDetailNames",
    "EWRNumber", "ApplicationDate", "LastResubmissionRequestDate", "ApprovalDate",
    "IssueDate", "BusinessDaysToApprove",
]

# ---------------------------------------------------------------------------
# Step 1: load the construction permit data
# ---------------------------------------------------------------------------

def load_construction_permits():
    """Upload the construction permit data in accordance with the instructions."""
    params = {
        "outFields": PERMITS_SELECT,
        "where": PERMITS_WHERE,
        "orderByFields": PERMITS_ORDER_BY,
        "returnGeometry": "false",
        "resultRecordCount": 2000,    # max records per request (according to the webpage)
        "f": "json",
    }

    rows = []
    while True:
        params["resultOffset"] = len(rows)
        response = requests.get(f"{PERMITS_URL}/query",
                                params=params,
                                timeout=60)
        response.raise_for_status()
        page = response.json()
        if "error" in page:  # ArcGIS returns query errors in the JSON body
            raise RuntimeError(page["error"])

        rows += [feature["attributes"] for feature in page["features"]]

        # The server flags when more records remain
        if not page.get("exceededTransferLimit"):
            break

    return pd.DataFrame(rows)

# Load the FY26 permit locations
locations = load_construction_permits()

# Look at the data
locations.info()

# ---------------------------------------------------------------------------
# Step 2: keep one row per permit
# ---------------------------------------------------------------------------

# Each row is one work location, so a permit (TrackingNumber) can have many
# rows. Keep each permit's most recently updated row (a few permits also have
# an older row with an earlier status)
permits = locations.drop_duplicates("TrackingNumber",
                                    keep="last")    # sorted by LastUpdateDate

# ---------------------------------------------------------------------------
# Step 3: correct the time stamps and count the business days to approve
# ---------------------------------------------------------------------------

def eastern_time(milliseconds):
    """Correct a time stamp column: the served Eastern clock time is really UTC."""
    served = (pd.to_datetime(milliseconds, unit="ms", utc=True)
              .dt.tz_convert("America/New_York")
              .dt.tz_localize(None))                  # the served Eastern clock time
    return (served.dt.tz_localize("UTC")              # ... is really UTC
            .dt.tz_convert("America/New_York")
            .dt.tz_localize(None))

permits["ApplicationDate"] = eastern_time(permits["ApplicationDate"])
permits["LastResubmissionRequestDate"] = eastern_time(permits["LastResubmissionRequestDate"])
permits["ApprovalDate"] = eastern_time(permits["LastApprovalDate"])
permits["IssueDate"] = eastern_time(permits["IssueDate"])

# Business days from the application date to the (last) approval date,
# leaving out weekends and DC holidays. The application day itself is not
# counted, so a permit approved the day it was applied for takes 0 days
permits["BusinessDaysToApprove"] = np.busday_count(
    permits["ApplicationDate"].values.astype("datetime64[D]"),
    permits["ApprovalDate"].values.astype("datetime64[D]"),
    holidays=list(DC_HOLIDAYS))

# ---------------------------------------------------------------------------
# Step 4: group each permit's work types into a permit type category
# ---------------------------------------------------------------------------

def permit_type_category(type_detail_names):
    """Category from the work types, e.g. 'Excavation; Repair Gas Main Line'.

    Each work type starts with its category and a semicolon. A permit with
    work types from more than one category is 'Multiple categories'.
    """
    categories = set(re.findall(r"(?:^|, )([^;,]+);", type_detail_names))
    if len(categories) == 1:
        return categories.pop()
    return "Multiple categories"

permits["PermitTypeCategory"] = permits["TypeDetailNames"].map(permit_type_category)

# Count each category
category_counts = (permits.groupby("PermitTypeCategory")
                   .size()
                   .sort_values(ascending=False))
print(category_counts)

# Look at the data
permits[OUTPUT_COLUMNS].info()

# Save the permits as a CSV for Tableau
here("data").mkdir(exist_ok=True)  # Create folder if it doesn't exist
permits[OUTPUT_COLUMNS].to_csv(here("data",
                                    "construction_permits_fy26.csv"),
                               index=False)
