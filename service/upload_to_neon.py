#!/usr/bin/env python3
"""
Upload final tokenomics CSV(s) to NEON (or any Postgres) so the Streamlit app
can load data from the database instead of large Supabase CSVs.

Usage:
  From project root:
    python -c "import sys; sys.path.insert(0, 'service'); from upload_to_neon import main; main()"
  Or:
    python service/upload_to_neon.py

Requires DATABASE_URL in .env (e.g. NEON connection string).
Run after create_final_dataset (e.g. at the end of main.py or monthly via cron).
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env")

# Main table: same data the app uses (Balancer-All-Tokenomics.csv)
CSV_ALL = DATA_DIR / "Balancer-All-Tokenomics.csv"
CSV_ORGANIZED = DATA_DIR / "Balancer-All-Tokenomics-Organized.csv"
TABLE_MAIN = "tokenomics"  # full dataset (app default)
TABLE_ORGANIZED = "tokenomics_organized"  # optional, complete records only


def get_engine():
    """Create SQLAlchemy engine from DATABASE_URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL not set. Add it to .env (e.g. from NEON dashboard: "
            "postgresql://user:pass@host/dbname?sslmode=require)"
        )
    try:
        from sqlalchemy import create_engine
    except ImportError:
        raise ImportError("Install sqlalchemy and psycopg2-binary: pip install sqlalchemy psycopg2-binary")
    # NEON and most Postgres need sslmode for pandas
    if "sslmode" not in url:
        url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
    return create_engine(url)


def upload_csv_to_table(engine, csv_path: Path, table_name: str, if_exists: str = "replace") -> int:
    """Load CSV and write to Postgres. Returns row count."""
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping table {table_name}.")
        return 0
    df = pd.read_csv(csv_path, nrows=0)
    columns = list(df.columns)
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"  ⚠️  {csv_path.name} is empty, skipping.")
        return 0
    # Normalize dates so they round-trip
    if "block_date" in df.columns:
        df["block_date"] = pd.to_datetime(df["block_date"], errors="coerce")
    df.to_sql(table_name, engine, method="multi", chunksize=10_000, index=False, if_exists=if_exists)
    print(f"  ✓ {table_name}: {len(df):,} rows from {csv_path.name}")
    return len(df)


def main():
    print("=" * 60)
    print("Upload tokenomics data to NEON (Postgres)")
    print("=" * 60)
    try:
        engine = get_engine()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    total = 0
    total += upload_csv_to_table(engine, CSV_ALL, TABLE_MAIN)
    upload_csv_to_table(engine, CSV_ORGANIZED, TABLE_ORGANIZED)
    print("=" * 60)
    print("Done. Set DATABASE_URL in the app environment so Streamlit loads from NEON.")
    print("=" * 60)


if __name__ == "__main__":
    main()
