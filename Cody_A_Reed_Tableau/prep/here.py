"""Project paths that work like R's here package, on Mac or Windows.

The prep script imports this the way an R script calls library(here):
    from here import here
    here("data", "permits.csv")   # -> <Tableau folder>/data/permits.csv
"""

from pathlib import Path

# Set project directory: the Tableau folder, one level above this prep folder
PROJECT_DIR = Path(__file__).resolve().parent.parent


# Function that mimics R's `here` package...
# Should work for Mac or Windows
def here(*parts):
    """Path inside the project folder, e.g. here("data", "permits.csv")."""
    return PROJECT_DIR.joinpath(*parts)
