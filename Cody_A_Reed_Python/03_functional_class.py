"""DDOT CS-12 Data Scientist assessment: Python test (Cody Arlie Reed).

Script 3 of the numbered scripts (run them in order):
    6. Merge the clean roadways onto the permit locations.
    7. Find the highest functional class for each permit.
    8. Write the final CSV: one row per permit location, with the functional
       class of that location and the highest functional class of its permit.

Reads:  data/utility_permit_locations_2026.csv.gz  (from 01_load_permits.py)
        data/lrs_roadways_fhwa.csv.gz              (from 02_lrs_roadways.py)
Writes: final_output/utility_permit_functional_class_2026.csv

Run from a terminal, from any folder:
    python 03_functional_class.py          (Windows: py 03_functional_class.py)
"""

import pandas as pd

from here import here

# ---------------------------------------------------------------------------
# Define global objects
# ---------------------------------------------------------------------------

# Setting the column types used to load the saved CSVs
PERMIT_COLUMN_TYPES = {
    "TrackingNumber": "int64",
    "PermitNumber": "str",
    "LocationID": "int64",
    "ApplicantCompany": "str",
    "EventTypeDescription": "str",
    "Status": "str",
    "ApplicationDate": "int64",          # milliseconds since 1970
    "IssueDate": "Int64",                # milliseconds since 1970; blank if not issued
    "WorkLocationFullAddress": "str",
    "geometry_x": "float64",
    "geometry_y": "float64",
    "Utility": "str",
}

ROADWAY_COLUMN_TYPES = {
    "geometry_x": "float64",
    "geometry_y": "float64",
    "SubBlockKey": "str",
    "RouteName": "str",
    "RouteType": "str",
    "UnitBlock": "str",
    "DistanceMeters": "float64",
    "DCFunctionalClassCode": "Int64",
    "DCFunctionalClass": "str",
    "FHWAFunctionalClassCode": "Int64",  # 1 = Interstate (highest) ... 7 = Local
    "FHWAFunctionalClass": "str",
}

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

# SELECT: setting the columns to keep in the final CSV, in order
OUTPUT_SELECT = [
    "TrackingNumber",
    "PermitNumber",
    "LocationID",
    "Utility",
    "ApplicantCompany",
    "EventTypeDescription",
    "Status",
    "ApplicationDate",
    "IssueDate",
    "WorkLocationFullAddress",
    "RouteName",
    "RouteType",
    "SubBlockKey",
    "FHWAFunctionalClassCode",
    "FHWAFunctionalClass",
    "HighestFHWAFunctionalClassCode",
    "HighestFHWAFunctionalClass",
    "geometry_x",
    "geometry_y",
]

# ORDER BY: setting each utility's permits and their locations to stay together
OUTPUT_ORDER_BY = [
    "Utility",
    "TrackingNumber",
    "LocationID",
]

# ---------------------------------------------------------------------------
# Load the permit locations and the roadways data
# ---------------------------------------------------------------------------

# Load the permit locations saved by 01_load_permits.py
permits = pd.read_csv(here("data",
                           "utility_permit_locations_2026.csv.gz"),
                      dtype=PERMIT_COLUMN_TYPES)

# Load the clean roadways with FHWA functional classes saved by 02_lrs_roadways.py
roadways = pd.read_csv(here("data",
                            "lrs_roadways_fhwa.csv.gz"),
                       dtype=ROADWAY_COLUMN_TYPES)

# ---------------------------------------------------------------------------
# Step 6: merge the roadways onto the permit locations
# ---------------------------------------------------------------------------

# Attach each location's roadway
permit_roadways = permits.merge(roadways,
                                on=["geometry_x",
                                    "geometry_y"],
                                # inner join so that we do not have missing observations
                                how="inner")

# Look at the data
permit_roadways.info()

# ---------------------------------------------------------------------------
# Step 7: find the highest functional class for each permit
# ---------------------------------------------------------------------------

# keep one row per location
highest_class_code = (permit_roadways.groupby("TrackingNumber")["FHWAFunctionalClassCode"]
                      .transform("min"))
permit_roadways["HighestFHWAFunctionalClassCode"] = highest_class_code
permit_roadways["HighestFHWAFunctionalClass"] = highest_class_code.map(FHWA_CLASS_NAMES)

# ---------------------------------------------------------------------------
# Step 8: write the final CSV, one row per permit location
# ---------------------------------------------------------------------------

def convert_dates(milliseconds):
    """Convert milliseconds since 1970 to calendar dates in Eastern time."""
    return (pd.to_datetime(milliseconds,
                           unit="ms",
                           utc=True)
            .dt.tz_convert("America/New_York")
            .dt.date)

# Keep the final columns and sort the rows
final_permits = (permit_roadways[OUTPUT_SELECT]
                 .sort_values(OUTPUT_ORDER_BY))

# Convert the dates to Eastern time so they are easier for the Associate
# Director to read
final_permits["ApplicationDate"] = convert_dates(final_permits["ApplicationDate"])
final_permits["IssueDate"] = convert_dates(final_permits["IssueDate"])

# Look at the data
final_permits.info()

# As of October 16, 2026: 4,890 permit locations and 19 variables
#   TrackingNumber                  permit application ID; may have several locations
#   PermitNumber                    assigned when the permit is issued (2,330 rows);
#                                   renewals reuse the original number plus -R1, -R2, ...
#   LocationID                      location within the application
#   Utility                         DC Water, PEPCO, or Washington Gas (set in step 2)
#   ApplicantCompany                company that applied; identifies the utility
#   EventTypeDescription            permit type (all Construction Staging Area)
#   Status                          e.g. ISSUED, EXPIRED, APPROVED, NOTPAID
#   ApplicationDate                 date applied, in Eastern time
#   IssueDate                       date issued, in Eastern time; blank for
#                                   applications not issued
#   WorkLocationFullAddress         block or address of the work location
#   RouteName                       name of the nearest roadway (from the LRS, step 3)
#   RouteType                       roadway type (alleys were filtered out in step 5)
#   SubBlockKey                     roadway SubBlock ID (the key for layer 162)
#   FHWAFunctionalClassCode         FHWA functional class of the location's roadway;
#                                   1 = Interstate (highest) ... 7 = Local
#   FHWAFunctionalClass             name of that functional class
#   HighestFHWAFunctionalClassCode  highest functional class among the permit's
#                                   locations (the lowest code; set in step 7)
#   HighestFHWAFunctionalClass      name of that functional class
#   geometry_x                      x coordinate
#   geometry_y                      y coordinate

# Save the final permit data as a CSV for the Associate Director
here("final_output").mkdir(exist_ok=True) # Create folder if it doesn't exist
final_permits.to_csv(here("final_output",
                          "utility_permit_functional_class_2026.csv"),
                     index=False)
