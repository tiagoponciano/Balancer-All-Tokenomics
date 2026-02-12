#!/usr/bin/env python3
"""
Get the latest block_date from existing tokenomics data (NEON or local CSV).
Used for incremental monthly runs: fetch only from (last_date + 1) to today.
"""
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(PROJECT_ROOT / ".env")

CSV_ORGANIZED = DATA_DIR / "Balancer-All-Tokenomics-Organized.csv"
CSV_ALL = DATA_DIR / "Balancer-All-Tokenomics.csv"
TABLE_MAIN = os.getenv("NEON_TABLE", "tokenomics").strip() or "tokenomics"
VEBAL_CSV = DATA_DIR / "veBAL.csv"
BRIBES_CSV = DATA_DIR / "Bribes.csv"
VOTES_EMISSIONS_CSV = DATA_DIR / "Votes_Emissions.csv"


def get_last_block_date_from_neon():
    """Query NEON for MAX(block_date). Returns date string YYYY-MM-DD or None."""
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        return None
    try:
        from sqlalchemy import create_engine, text
        if "sslmode" not in url:
            url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
        engine = create_engine(url)
        with engine.connect() as conn:
            # Use quoted identifier for case-sensitive table names
            row = conn.execute(text(f'SELECT MAX(block_date) AS d FROM "{TABLE_MAIN}"')).fetchone()
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


def _last_date_from_csv(path: Path, date_column: str) -> str | None:
    """Read a CSV, return max date from date_column as YYYY-MM-DD or None."""
    if not path.exists() or path.stat().st_size < 10:
        return None
    try:
        import pandas as pd
        df = pd.read_csv(path, usecols=[date_column], nrows=0)
        if date_column not in df.columns:
            return None
        df = pd.read_csv(path, usecols=[date_column])
        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
        max_d = df[date_column].max()
        if pd.notna(max_d):
            return max_d.strftime("%Y-%m-%d") if hasattr(max_d, "strftime") else str(max_d)[:10]
    except Exception:
        pass
    return None


def get_last_date_per_source():
    """
    Return last date from each data source (for testing incremental logic).
    Keys: source name, values: last date YYYY-MM-DD or None if missing/empty.
    """
    out = {}
    # Main tokenomics (used for incremental start_date)
    last = get_last_block_date_from_neon()
    if last:
        out["NEON (table: " + TABLE_MAIN + ")"] = last
    else:
        out["NEON (table: " + TABLE_MAIN + ")"] = None
    out["Balancer-All-Tokenomics (local)"] = get_last_block_date_from_csv()
    out["veBAL.csv"] = _last_date_from_csv(VEBAL_CSV, "block_date")
    out["Bribes.csv"] = _last_date_from_csv(BRIBES_CSV, "day")
    out["Votes_Emissions.csv"] = _last_date_from_csv(VOTES_EMISSIONS_CSV, "day")
    return out
