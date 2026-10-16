"""Project paths that work like R's here package, on Mac or Windows.

Each numbered script imports this the way an R script calls library(here):
    from here import here
    here("data", "lrs_roadways.csv.gz")   # -> <this folder>/data/lrs_roadways.csv.gz
"""

from pathlib import Path

# Set project directory: the folder this file is in
PROJECT_DIR = Path(__file__).resolve().parent


# Function that mimics R's `here` package...
# Should work for Mac or Windows
def here(*parts):
    """Path inside the project folder, e.g. here("final_output")."""
    return PROJECT_DIR.joinpath(*parts)
