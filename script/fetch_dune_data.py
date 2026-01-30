#!/usr/bin/env python3
"""
Legacy script to fetch data from Dune and generate CSV
(Use main.py for multiple queries)
"""
from pathlib import Path
from dune_fetcher import fetch_and_save

API_KEY = "QTKSQUbw3YzhNCLgsXqEbEZG7iJheA3z"
QUERY_ID = 6623057
OUTPUT_FILE = "veBAL.csv"

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    """
    Main function to fetch data from Dune and generate CSV.
    
    Fetches data from a single Dune query and saves it to a CSV file.
    This is a legacy script - use main.py for processing multiple queries.
    
    Returns:
        Tuple (success: bool, rows: int, path: Path) from fetch_and_save
    """
    fetch_and_save(
        api_key=API_KEY,
        query_id=QUERY_ID,
        output_filename=OUTPUT_FILE,
        project_root=PROJECT_ROOT
    )


if __name__ == "__main__":
    main()
