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
TABLE_MAIN = os.getenv("NEON_TABLE", "tokenomics").strip() or "tokenomics"
TABLE_ORGANIZED = TABLE_MAIN + "_organized"


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


def _get_last_block_date(engine, table_name: str):
    """Get MAX(block_date) from table. Returns datetime or None."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            row = conn.execute(text(f'SELECT MAX(block_date) AS d FROM "{table_name}"')).fetchone()
        if row and row[0] is not None:
            return pd.Timestamp(row[0])
        return None
    except Exception:
        return None


def upload_csv_to_table(engine, csv_path: Path, table_name: str, if_exists: str = "replace", append_only: bool = False) -> int:
    """Load CSV and write to Postgres. Returns row count.
    If append_only=True, only inserts rows with block_date > MAX(block_date) in table (concatenate new data)."""
    if not csv_path.exists():
        print(f"  ⚠️  {csv_path.name} not found, skipping table {table_name}.")
        return 0
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"  ⚠️  {csv_path.name} is empty, skipping.")
        return 0
    # Normalize dates so they round-trip
    if "block_date" in df.columns:
        df["block_date"] = pd.to_datetime(df["block_date"], errors="coerce")

    if append_only:
        last = _get_last_block_date(engine, table_name)
        if last is not None:
            df = df[df["block_date"] > last]
            if len(df) == 0:
                print(f"  ✓ {table_name}: no new rows (all block_date <= {last.date()})")
                return 0
            print(f"  ℹ Appending {len(df):,} new rows (block_date > {last.date()})")
            df.to_sql(table_name, engine, method="multi", chunksize=10_000, index=False, if_exists="append")
        else:
            print(f"  ℹ Table empty or missing—inserting all {len(df):,} rows (first run)")
            df.to_sql(table_name, engine, method="multi", chunksize=10_000, index=False, if_exists="replace")
    else:
        df.to_sql(table_name, engine, method="multi", chunksize=10_000, index=False, if_exists=if_exists)
    print(f"  ✓ {table_name}: {len(df):,} rows from {csv_path.name}")
    return len(df)


def refresh_materialized_views(engine):
    """Refresh mv_pool_summary and mv_monthly_series after loading new data.
    Uses CONCURRENTLY so the app can keep reading; requires autocommit (CONCURRENTLY
    cannot run inside a transaction block)."""
    VIEWS = ["mv_pool_summary", "mv_monthly_series", "mv_daily_series"]
    try:
        from sqlalchemy import text
        # CONCURRENTLY must run outside a transaction; use autocommit
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for view in VIEWS:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                print(f"  ✓ Refreshed {view}")
    except Exception as e:
        print(f"  ⚠️  Could not refresh views: {e}")
        print("  (Make sure you ran sql/neon_materialized_views.sql and have USE_NEON_VIEWS=1)")


def main(refresh_views: bool = None, append_only: bool = None):
    _append = append_only if append_only is not None else os.getenv("UPLOAD_APPEND", "").strip().lower() in ("1", "true", "yes")
    print("=" * 60)
    print("Upload tokenomics data to NEON (Postgres)")
    if _append:
        print("Mode: APPEND (only new block_date rows)")
    print("=" * 60)
    try:
        engine = get_engine()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    total = 0
    total += upload_csv_to_table(engine, CSV_ALL, TABLE_MAIN, append_only=_append)
    if not _append:
        upload_csv_to_table(engine, CSV_ORGANIZED, TABLE_ORGANIZED)
    # Refresh materialized views if USE_NEON_VIEWS or --refresh-views
    do_refresh = refresh_views if refresh_views is not None else os.getenv("USE_NEON_VIEWS", "").strip() in ("1", "true", "yes")
    if do_refresh and total > 0:
        print("\nRefreshing materialized views...")
        refresh_materialized_views(engine)
    print("=" * 60)
    print("Done. Set DATABASE_URL in the app environment so Streamlit loads from NEON.")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Upload tokenomics CSVs to NEON")
    p.add_argument("--append", action="store_true", help="Append only new data (block_date > last in table). Use for incremental updates.")
    p.add_argument("--refresh-views", action="store_true", help="Refresh mv_pool_summary and mv_monthly_series after upload")
    p.add_argument("--no-refresh-views", action="store_true", help="Skip view refresh even if USE_NEON_VIEWS=1")
    args = p.parse_args()
    refresh = True if args.refresh_views else (False if args.no_refresh_views else None)
    main(refresh_views=refresh, append_only=args.append)
