#!/usr/bin/env python3
"""
Get the latest block_date from existing tokenomics data (NEON or local CSV).
Used for incremental monthly runs: fetch only from (last_date + 1) to today.
"""
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CSV_ORGANIZED = DATA_DIR / "Balancer-All-Tokenomics-Organized.csv"
CSV_ALL = DATA_DIR / "Balancer-All-Tokenomics.csv"
TABLE_MAIN = "tokenomics"


def get_last_block_date_from_neon():
    """Query NEON for MAX(block_date). Returns date string YYYY-MM-DD or None."""
    import os
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        return None
    try:
        from sqlalchemy import create_engine, text
        if "sslmode" not in url:
            url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
        engine = create_engine(url)
        with engine.connect() as conn:
            row = conn.execute(text(f"SELECT MAX(block_date) AS d FROM {TABLE_MAIN}")).fetchone()
        if row and row[0] is not None:
            d = row[0]
            if hasattr(d, "strftime"):
                return d.strftime("%Y-%m-%d")
            return str(d)[:10]
    except Exception:
        pass
    return None


def get_last_block_date_from_csv():
    """Read local final CSV and return latest block_date as YYYY-MM-DD or None."""
    for path in (CSV_ORGANIZED, CSV_ALL):
        if not path.exists() or path.stat().st_size < 100:
            continue
        try:
            import pandas as pd
            df = pd.read_csv(path, usecols=["block_date"], nrows=0)
            if "block_date" not in df.columns:
                continue
            df = pd.read_csv(path, usecols=["block_date"])
            df["block_date"] = pd.to_datetime(df["block_date"], errors="coerce")
            max_d = df["block_date"].max()
            if pd.notna(max_d):
                if hasattr(max_d, "strftime"):
                    return max_d.strftime("%Y-%m-%d")
                return str(max_d)[:10]
        except Exception:
            continue
    return None


def get_last_block_date():
    """Try NEON first, then local CSV. Returns YYYY-MM-DD or None."""
    last = get_last_block_date_from_neon()
    if last:
        return last
    return get_last_block_date_from_csv()


def get_incremental_date_range(default_start: str = "2024-01-01"):
    """
    For incremental monthly runs: start the day after the last record, end today.
    If no existing data, use default_start to today.
    Returns (start_date, end_date, last_date_or_none) as 'YYYY-MM-DD' strings.
    """
    from datetime import timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    last = get_last_block_date()
    if not last:
        return default_start, today, None
    try:
        last_d = datetime.strptime(last, "%Y-%m-%d")
        next_d = last_d + timedelta(days=1)
        start = next_d.strftime("%Y-%m-%d")
        if start > today:
            return last, today, last
        return start, today, last
    except Exception:
        return default_start, today, None
