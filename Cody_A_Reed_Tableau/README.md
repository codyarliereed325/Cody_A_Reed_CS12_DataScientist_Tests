# Tableau test: business days to approve construction permits, FY26

Cody A. Reed · DDOT CS-12 Data Scientist Assessment · Tableau test

- `DDOT_FY26_Permit_Approval_Times.twbx`: the packaged workbook (Tableau Desktop 2026.2). It opens on the dashboard.
- `prep/01_prepare_permits.py`: downloads the permits from DDOT's REST service and writes `data/construction_permits_fy26.csv` (one row per permit). `prep/here.py` builds the file paths.
- `thought_process.pdf`: how I approached the test, and why.

To rebuild the data (Python 3 with pandas, numpy, and requests):

```
py prep\01_prepare_permits.py          (Mac: python prep/01_prepare_permits.py)
```
