#!/usr/bin/env python3
"""
Script to classify pools as core or non-core based on historical CSV data.

Classification logic:
A pool is CORE on date D if there exists a row in the historical CSV such that:
- address = pool_address
- D >= added_date
- (removed_date IS NULL OR D < removed_date)

Otherwise, it is NON-CORE.

Requirements:
1. Core pools history file (classification_core_pools.csv):
   - Must contain columns: 'address', 'added_date', 'removed_date' (optional)
   - Each row represents a period when a pool was a Core Pool
   - removed_date can be NULL if the pool is still a Core Pool

2. Daily dataset (veBAL.csv by default):
   - Must contain columns with pool address and date
   - The script automatically detects columns with names like:
     * Address: 'project_contract_address', 'address', 'pool_address', etc.
     * Date: 'block_date', 'date', 'day', 'timestamp', etc.

3. Output file:
   - classification_core_pools.csv with columns: 'address', 'day', 'is_core'
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

CORE_POOLS_HISTORY_FILE = DATA_DIR / "classification_core_pools.csv"
DAILY_DATASET_FILE = DATA_DIR / "veBAL.csv"
OUTPUT_FILE = DATA_DIR / "classification_core_pools.csv"


def classify_core_pools(
    core_pools_file: Path = CORE_POOLS_HISTORY_FILE,
    daily_dataset_file: Path = DAILY_DATASET_FILE,
    output_file: Path = OUTPUT_FILE
):
    """
    Classifies pools as core or non-core based on historical data.
    
    A pool is classified as CORE on a given date if there exists a record
    in the historical CSV where the pool address matches, the date is greater
    than or equal to added_date, and either removed_date is NULL or the date
    is less than removed_date. Otherwise, the pool is classified as NON-CORE.
    
    Args:
        core_pools_file: Path to the core pools history CSV file
        daily_dataset_file: Path to the daily dataset CSV file
        output_file: Path to the output CSV file
        
    Returns:
        DataFrame with classification results containing columns:
        'address', 'day', 'is_core'
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing or cannot be detected
    """
    print("=" * 60)
    print("🚀 Core Pools Classification")
    print("=" * 60)
    
    print("\n📖 Reading files...")
    
    if not core_pools_file.exists():
        raise FileNotFoundError(f"File not found: {core_pools_file}")
    if not daily_dataset_file.exists():
        raise FileNotFoundError(f"File not found: {daily_dataset_file}")
    
    core_pools_df = pd.read_csv(core_pools_file)
    daily_df = pd.read_csv(daily_dataset_file)
    
    print(f"✅ Core pools CSV: {len(core_pools_df):,} rows")
    print(f"✅ Daily dataset: {len(daily_df):,} rows")
    
    print(f"\n📋 Columns in core pools history: {list(core_pools_df.columns)}")
    print(f"📋 Columns in daily dataset: {list(daily_df.columns)}")
    
    required_core_cols = ['address', 'added_date']
    missing_core = [col for col in required_core_cols if col not in core_pools_df.columns]
    
    if missing_core:
        raise ValueError(f"Missing columns in core pools history: {missing_core}")
    
    address_col = None
    date_col = None
    
    address_candidates = ['project_contract_address', 'address', 'pool_address', 'pool_id', 'contract_address']
    for col in address_candidates:
        if col in daily_df.columns:
            address_col = col
            break
    
    date_candidates = ['block_date', 'date', 'day', 'timestamp', 'block_timestamp']
    for col in date_candidates:
        if col in daily_df.columns:
            date_col = col
            break
    
    if address_col is None:
        raise ValueError(
            f"Could not find address column in daily dataset. "
            f"Available columns: {list(daily_df.columns)}. "
            f"Try renaming a column to one of these names: {address_candidates}"
        )
    
    if date_col is None:
        raise ValueError(
            f"Could not find date column in daily dataset. "
            f"Available columns: {list(daily_df.columns)}. "
            f"Try renaming a column to one of these names: {date_candidates}"
        )
    
    print(f"\n✅ Detected columns:")
    print(f"   Address: {address_col}")
    print(f"   Date: {date_col}")
    
    print("\n🔄 Converting dates...")
    core_pools_df['added_date'] = pd.to_datetime(core_pools_df['added_date'], errors='coerce')
    
    if 'removed_date' not in core_pools_df.columns:
        core_pools_df['removed_date'] = pd.NaT
    else:
        core_pools_df['removed_date'] = pd.to_datetime(core_pools_df['removed_date'], errors='coerce')
    
    daily_df[date_col] = pd.to_datetime(daily_df[date_col], errors='coerce')
    
    def remove_timezone(series):
        """
        Removes timezone from a datetime series if it exists.
        
        Args:
            series: Pandas Series with datetime values
            
        Returns:
            Series with timezone removed (tz-naive)
        """
        try:
            if hasattr(series.dt, 'tz') and series.dt.tz is not None:
                return series.dt.tz_localize(None)
        except (AttributeError, TypeError):
            pass
        return series
    
    core_pools_df['added_date'] = remove_timezone(core_pools_df['added_date'])
    core_pools_df['removed_date'] = remove_timezone(core_pools_df['removed_date'])
    daily_df[date_col] = remove_timezone(daily_df[date_col])
    
    initial_daily_count = len(daily_df)
    daily_df = daily_df.dropna(subset=[date_col])
    core_pools_df = core_pools_df.dropna(subset=['added_date'])
    
    if len(daily_df) < initial_daily_count:
        print(f"⚠️  Removed {initial_daily_count - len(daily_df):,} rows with invalid dates from daily dataset")
    
    print(f"✅ Daily dataset after cleaning: {len(daily_df):,} rows")
    print(f"✅ Core pools history after cleaning: {len(core_pools_df):,} rows")
    
    print("\n🔍 Classifying pools...")
    
    result_df = daily_df[[address_col, date_col]].copy()
    result_df.columns = ['address', 'day']
    result_df = result_df.drop_duplicates()
    
    print(f"📊 Total unique combinations (address, day): {len(result_df):,}")
    
    merged = result_df.merge(
        core_pools_df[['address', 'added_date', 'removed_date']],
        on='address',
        how='left',
        suffixes=('', '_core')
    )
    
    print(f"📊 Total combinations after merge: {len(merged):,}")
    
    valid_intervals = merged[
        (merged['day'] >= merged['added_date'])
    ].copy()
    
    valid_intervals['is_valid_interval'] = (
        valid_intervals['removed_date'].isna() | 
        (valid_intervals['day'] < valid_intervals['removed_date'])
    )
    
    core_intervals = valid_intervals[valid_intervals['is_valid_interval']]
    
    core_classification = core_intervals.groupby(['address', 'day']).size().reset_index(name='count')
    core_classification['is_core'] = True
    
    result_df = result_df.merge(
        core_classification[['address', 'day', 'is_core']],
        on=['address', 'day'],
        how='left'
    )
    
    result_df['is_core'] = result_df['is_core'].fillna(False).astype(bool)
    
    total_rows = len(result_df)
    core_rows = result_df['is_core'].sum()
    non_core_rows = total_rows - core_rows
    
    print(f"\n📊 Statistics:")
    print(f"  Total unique combinations: {total_rows:,}")
    print(f"  Core: {core_rows:,} ({100 * core_rows / total_rows:.2f}%)")
    print(f"  Non-core: {non_core_rows:,} ({100 * non_core_rows / total_rows:.2f}%)")
    
    result_df = result_df.sort_values(['address', 'day'])
    
    print(f"\n💾 Saving result to {output_file}...")
    result_df.to_csv(output_file, index=False)
    
    print(f"✅ File saved successfully!")
    print(f"   Total rows in output file: {len(result_df):,}")
    
    print("\n📋 Results sample (first 20 rows):")
    print(result_df.head(20).to_string(index=False))
    
    print("\n🔍 Validation - Checking specific cases:")
    
    sample_addresses = result_df['address'].unique()[:3]
    
    for address in sample_addresses:
        address_data = result_df[result_df['address'] == address].head(10)
        if len(address_data) > 0:
            print(f"\n  Address: {address}")
            print(address_data.to_string(index=False))
    
    print("\n🔍 Checking Core <-> Non-Core transitions:")
    transitions = []
    for address in result_df['address'].unique()[:5]:
        addr_data = result_df[result_df['address'] == address].sort_values('day')
        if len(addr_data) > 1:
            changes = addr_data['is_core'].ne(addr_data['is_core'].shift()).sum()
            if changes > 0:
                transitions.append({
                    'address': address,
                    'transitions': changes,
                    'first_date': addr_data['day'].min(),
                    'last_date': addr_data['day'].max()
                })
    
    if transitions:
        transitions_df = pd.DataFrame(transitions)
        print(transitions_df.to_string(index=False))
    
    return result_df


def main():
    """
    Main function to execute the core pools classification process.
    
    Returns:
        DataFrame with classification results containing columns:
        'address', 'day', 'is_core'
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing or cannot be detected
    """
    try:
        result_df = classify_core_pools()
        print("\n" + "=" * 60)
        print("✅ Process completed successfully!")
        print("=" * 60)
        return result_df
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
