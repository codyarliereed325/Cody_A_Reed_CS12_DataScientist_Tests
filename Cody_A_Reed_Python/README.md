# Utility Permit Functional Class Enrichment

Cody A. Reed · DDOT CS-12 Data Scientist Assessment · Python test

This tool enriches the 2026 Public Space Occupancy Permit locations of DC Water, PEPCO, and Washington Gas with the FHWA functional class of the road at each location, and adds the highest functional class of each permit.

**Final output:** `final_output/utility_permit_functional_class_2026.csv`, one row per permit location.

## Folder contents

```
01_load_permits.py        download the 2026 utility permit locations
02_lrs_roadways.py        find the roadway and FHWA functional class at each location
03_functional_class.py    find each permit's highest class and write the final CSV
here.py                   builds file paths from this folder, so they work on Windows
requirements.txt          Python packages
thought_process.pdf       how I approached the test, and why
data/                     files passed between the scripts, from my run on October 16, 2026
final_output/             the final CSV
```

## How it works

1. **`01_load_permits.py`** queries DDOT's [occupancy permit layer](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_APPS/DDOT_TOPS/MapServer/24) with SQL. It keeps permits of the two requested types that were applied for or issued in 2026, runs one query per utility, and saves `data/utility_permit_locations_2026.csv.gz`.
2. **`02_lrs_roadways.py`** sends each unique permit coordinate to DDOT's linear referencing system (LRS). Its [`getPointOnSubBlock`](https://rh.dcgis.dc.gov/dcgis/rest/services/DDOT/RoadwayBlocks/MapServer/exts/DdotLrsExtensions/getPointOnSubBlock) tool returns the nearest roadway and its `SubBlockKey`, and the script saves these lookups as `data/lrs_roadways.csv.gz`. It then gets the FHWA functional class of each `SubBlockKey` from the [Roadway SubBlock layer](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Transportation_WebMercator/MapServer/162), drops alleys and other roadways without a class, and saves `data/lrs_roadways_fhwa.csv.gz`.
3. **`03_functional_class.py`** joins the roadways to the permit locations, finds each permit's highest functional class, and writes the final CSV.

## How to run (Windows 11)

You need Python 3.11 or newer and an internet connection. In Command Prompt or PowerShell:

```
cd path\to\Cody_A_Reed_Python
py -m pip install -r requirements.txt
py 01_load_permits.py
py 02_lrs_roadways.py
py 03_functional_class.py
```

- To install the packages in a virtual environment instead, run `py -m venv .venv` first and use `.venv\Scripts\python` in place of `py`.
- The scripts can be run from any folder or from an editor such as VS Code. To run lines one at a time in an editor, open the `Cody_A_Reed_Python` folder itself.
- `01` and `03` take under a minute. `02` sends about 3,400 requests to the LRS and takes about 9 minutes.
- `data/` already holds the files from my run, so `03` can be run on its own. If you rerun `01`, rerun `02` before `03`.
- Close the final CSV in Excel before running `03`; Windows will not let the script overwrite an open file.

## Settings

Each script defines its settings at the top, with comments.

| Setting | Script | Current value |
|---|---|---|
| `OCCUPANCY_WHERE` | `01` | Applied for or issued in 2026; Construction Staging Area or Mobile Crane Work Zone |
| `UTILITY_WHERE` | `01` | The `ApplicantCompany` values of each utility |
| `LRS_SEARCH_RADIUS` | `02` | 50 meters |
| `LRS_WORKERS` | `02` | 8 requests at a time |
| `OUTPUT_SELECT`, `OUTPUT_ORDER_BY` | `03` | Columns and row order of the final CSV |

## Final CSV

`final_output/utility_permit_functional_class_2026.csv` has one row per permit location (4,890 rows from my run), sorted by utility, permit, and location.

| Column | Description |
|---|---|
| `TrackingNumber` | Permit application ID |
| `PermitNumber` | Permit number; blank until the permit is issued |
| `LocationID` | Location within the permit application |
| `Utility` | DC Water, PEPCO, or Washington Gas |
| `ApplicantCompany` | Applicant name in the permit system |
| `EventTypeDescription` | Permit type |
| `Status` | Permit status, such as ISSUED or APPROVED |
| `ApplicationDate`, `IssueDate` | Dates in Eastern time; `IssueDate` is blank until the permit is issued |
| `WorkLocationFullAddress` | Work location from the permit |
| `RouteName`, `RouteType` | Roadway the LRS matched to the location |
| `SubBlockKey` | DDOT ID of that roadway segment |
| `FHWAFunctionalClassCode`, `FHWAFunctionalClass` | FHWA functional class of the location |
| `HighestFHWAFunctionalClassCode`, `HighestFHWAFunctionalClass` | Highest FHWA functional class among the permit's locations |
| `geometry_x`, `geometry_y` | Location coordinates in Web Mercator (EPSG:3857) |

FHWA codes run from 1 (Interstate, the highest class) to 7 (Local, the lowest), so a permit's highest class is the lowest code among its locations.

## Assumptions and limitations

- **2026.** A record counts if it was applied for or issued in 2026, whatever its status. Filter on `Status` to leave out withdrawn or rejected applications.
- **Utilities.** Each utility is identified by its `ApplicantCompany` values: 'DCWater/CIP', 'DCWater/OPS', and 'DCWater' for DC Water; 'Potomac Electric Power Company' and 'Pepco' for PEPCO; and 'Wash Gas & Light Co.' for Washington Gas. Other companies that file these permits, such as telecom providers, are left out.
- **Permit types.** The layer has no Mobile Crane Work Zone permits from these utilities, so every row is a Construction Staging Area.
- **Alleys.** Alleys have no functional class, so locations whose nearest roadway is an alley are left out, along with the few driveways and a walkway that also have no class. This removes 148 of 5,038 locations and 116 of 3,149 permits.
- **Street corners.** For about 1.5% of locations, the matched roadway is not the street in the permit address, mostly at corners where the LRS returned the cross street. The LRS can return either street at a corner, so a new run can differ at a few locations (7 of 4,890 in a test rerun).
- **LRS rather than MAR.** The MAR API requires an API key; the LRS does not.
- **Live data.** The counts are from October 16, 2026. The permit layer is rebuilt every night and keeps only recent permits; the earliest expiration date in it is September 2, 2026. Permits from early 2026 that expired before then are not in the data, and a new run can return different counts.
