#!/usr/bin/env python3
"""
Dune fetcher with chunking support for large queries
"""
from dune_client.client import DuneClient
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional, Tuple
import time
import pandas as pd
from pathlib import Path


def fetch_dune_query_with_params(
    api_key: str, 
    query_id: int, 
    params: Dict[str, str]
) -> Optional[List[Dict]]:
    """
    Fetches data from a Dune query with parameters
    
    Args:
        api_key: Dune API key
        query_id: Dune query ID
        params: Dictionary of parameters (e.g., {'start_date': '2024-01-01', 'end_date': '2024-03-01'})
    
    Returns:
        List of dictionaries with query data, or None if failed
    """
    try:
        from dune_client.types import QueryParameter
        from dune_client.query import QueryBase
        
        dune = DuneClient(api_key)
        
        # Convert params to QueryParameter objects
        query_params = [
            QueryParameter.text_type(name=key, value=value)
            for key, value in params.items()
        ]
        
        # Create query object
        query = QueryBase(
            query_id=query_id,
            params=query_params
        )
        
        # Execute query with parameters
        query_result = dune.run_query(query)
        
        if not query_result or not hasattr(query_result, 'result') or not query_result.result:
            return None
        
        result = query_result.result
        rows = result.rows if hasattr(result, 'rows') and result.rows else []
        
        return rows if rows else None
        
    except Exception as e:
        print(f"Error fetching query {query_id} with params {params}: {str(e)}")
        return None


def fetch_chunked_query(
    api_key: str,
    query_id: int,
    start_date: str,
    end_date: str,
    chunk_months: Optional[int] = None,
    chunk_days: Optional[int] = 45
) -> Optional[List[Dict]]:
    """
    Fetches a Dune query in chunks based on date ranges.
    Uses chunk_days if set (default 45), otherwise chunk_months.
    
    Args:
        api_key: Dune API key
        query_id: Dune query ID
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        chunk_months: Number of months per chunk (ignored if chunk_days is set)
        chunk_days: Number of days per chunk (default: 45)
    
    Returns:
        Combined list of all rows from all chunks
    """
    use_days = chunk_days is not None and chunk_days > 0
    chunk_label = f"{chunk_days}-day" if use_days else f"{chunk_months or 2}-month"
    print(f"\n📊 Fetching query {query_id} in {chunk_label} chunks...")
    print(f"   Date range: {start_date} to {end_date}")
    
    # Parse dates
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_rows = []
    current_start = start
    chunk_num = 0
    
    while current_start <= end:
        chunk_num += 1
        
        # Calculate chunk end date
        if use_days:
            chunk_end = current_start + timedelta(days=chunk_days) - timedelta(days=1)
        else:
            chunk_end = current_start + relativedelta(months=chunk_months or 2) - timedelta(days=1)
        if chunk_end > end:
            chunk_end = end
        
        # Format dates for Dune
        chunk_start_str = current_start.strftime('%Y-%m-%d')
        chunk_end_str = chunk_end.strftime('%Y-%m-%d')
        
        print(f"\n   Chunk {chunk_num}: {chunk_start_str} to {chunk_end_str}")
        
        # Fetch this chunk (retry up to 2 times on failure)
        params = {
            'start_date': chunk_start_str,
            'end_date': chunk_end_str
        }
        rows = None
        for attempt in range(3):
            rows = fetch_dune_query_with_params(api_key, query_id, params)
            if rows is not None:
                break
            if attempt < 2:
                print(f"   ⚠ Retry {attempt + 2}/3 in 5s...")
                time.sleep(5)
        
        if rows:
            all_rows.extend(rows)
            print(f"   ✓ Fetched {len(rows):,} rows")
        else:
            print(f"   ⚠ No data returned for this chunk (all retries failed)")
        
        # Move to next chunk
        current_start = chunk_end + timedelta(days=1)
    
    print(f"\n   ✓ Total rows fetched: {len(all_rows):,}")
    
    return all_rows if all_rows else None


def fetch_and_save_chunked(
    api_key: str,
    query_id: int,
    start_date: str,
    end_date: str,
    output_filename: str,
    project_root: Path,
    chunk_months: Optional[int] = None,
    chunk_days: Optional[int] = 45,
    merge_with_existing: bool = False,
) -> Tuple[bool, int, Optional[Path]]:
    """
    Fetches a chunked Dune query and saves to CSV.
    Uses chunk_days (default 45) for smaller, less timeout-prone requests.
    If merge_with_existing=True, appends to existing CSV (for incremental runs).
    
    Args:
        api_key: Dune API key
        query_id: Dune query ID
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        output_filename: Name of output CSV file
        project_root: Project root path
        chunk_months: Number of months per chunk (ignored if chunk_days is set)
        chunk_days: Number of days per chunk (default: 45)
    
    Returns:
        Tuple of (success, row_count, output_path)
    """
    print(f"\n{'='*60}")
    print(f"Processing Query {query_id} (CHUNKED)")
    print(f"{'='*60}")
    
    output_dir = project_root / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / output_filename

    try:
        # Fetch data in chunks
        rows = fetch_chunked_query(
            api_key=api_key,
            query_id=query_id,
            start_date=start_date,
            end_date=end_date,
            chunk_months=chunk_months,
            chunk_days=chunk_days
        )
        
        if not rows:
            print(f"✗ No data returned for query {query_id}")
            return False, 0, None
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Remove duplicates (in case of overlapping data at chunk boundaries)
        initial_count = len(df)
        df = df.drop_duplicates()
        if len(df) < initial_count:
            print(f"   ℹ Removed {initial_count - len(df)} duplicate rows")
        
        # Incremental: merge with existing file so we keep full history
        if merge_with_existing and output_path.exists() and output_path.stat().st_size > 0:
            try:
                existing = pd.read_csv(output_path)
                key_cols = [c for c in ["blockchain", "project_contract_address", "block_date"] if c in existing.columns and c in df.columns]
                if not key_cols:
                    key_cols = list(existing.columns[:3]) if len(existing.columns) >= 3 else list(existing.columns)
                combined = pd.concat([existing, df], ignore_index=True)
                before = len(combined)
                combined = combined.drop_duplicates(subset=key_cols, keep="last")
                if len(combined) < before:
                    print(f"   ℹ Merged with existing: {len(existing):,} + {len(df):,} → {len(combined):,} (removed {before - len(combined)} duplicates)")
                else:
                    print(f"   ℹ Merged with existing: {len(existing):,} + {len(df):,} → {len(combined):,}")
                df = combined
            except Exception as e:
                print(f"   ⚠ Could not merge with existing file: {e}. Overwriting.")
        
        df.to_csv(output_path, index=False)
        
        print(f"✓ Successfully saved {len(df):,} rows to {output_filename}")
        print(f"{'='*60}")
        
        return True, len(df), output_path
        
    except Exception as e:
        print(f"✗ Error processing query {query_id}: {str(e)}")
        print(f"{'='*60}")
        return False, 0, None


def fetch_and_save_with_params(
    api_key: str,
    query_id: int,
    params: Dict[str, str],
    output_filename: str,
    project_root: Path,
    merge_with_existing: bool = False,
    merge_key_columns: Optional[List[str]] = None,
) -> Tuple[bool, int, Optional[Path]]:
    """
    Fetches a Dune query with parameters (e.g. start_date, end_date) and saves to CSV.
    Used for Bribes (start_date) and Votes_Emissions (start_date, end_date).
    When merge_with_existing=True, appends to existing file and dedupes (for incremental runs).
    """
    output_dir = project_root / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / output_filename

    try:
        print(f"\n{'='*60}")
        print(f"Processing Query {query_id} (with params)")
        print(f"  Params: {params}")
        print(f"{'='*60}")
        rows = fetch_dune_query_with_params(api_key, query_id, params)
        if not rows:
            print(f"✗ No data returned for query {query_id}")
            return False, 0, None

        df = pd.DataFrame(rows)
        df = df.drop_duplicates()

        if merge_with_existing and output_path.exists() and output_path.stat().st_size > 0:
            try:
                existing = pd.read_csv(output_path)
                key_cols = merge_key_columns or []
                if not key_cols:
                    key_cols = [c for c in ["day", "proposal_hash", "gauge_address"] if c in existing.columns and c in df.columns]
                if not key_cols and len(existing.columns) >= 2:
                    key_cols = list(existing.columns[:2])
                combined = pd.concat([existing, df], ignore_index=True)
                before = len(combined)
                combined = combined.drop_duplicates(subset=key_cols, keep="last")
                if len(combined) < before:
                    print(f"   ℹ Merged with existing: {len(existing):,} + {len(df):,} → {len(combined):,} (removed {before - len(combined)} duplicates)")
                else:
                    print(f"   ℹ Merged with existing: {len(existing):,} + {len(df):,} → {len(combined):,}")
                df = combined
            except Exception as e:
                print(f"   ⚠ Could not merge with existing file: {e}. Overwriting.")

        df.to_csv(output_path, index=False)
        print(f"✓ Successfully saved {len(df):,} rows to {output_filename}")
        print(f"{'='*60}")
        return True, len(df), output_path
    except Exception as e:
        print(f"✗ Error processing query {query_id}: {str(e)}")
        print(f"{'='*60}")
        return False, 0, None