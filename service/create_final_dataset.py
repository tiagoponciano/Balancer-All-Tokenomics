#!/usr/bin/env python3
"""
Script to create the final dataset by combining veBAL.csv and votes_bribes_merged.csv

Merge based on:
- gauge_address
- block_date (veBAL) = day (votes_bribes_merged)
- blockchain

Keeps all rows regardless of gauge_address presence (filtering can be done in the UI).
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

VEBAL_FILE = DATA_DIR / "veBAL.csv"
VOTES_BRIBES_FILE = DATA_DIR / "votes_bribes_merged.csv"
CORE_POOLS_CLASSIFICATION_FILE = DATA_DIR / "classification_core_pools.csv"
OUTPUT_FILE = DATA_DIR / "Balancer-All-Tokenomics.csv"

FINAL_COLUMNS = [
    'blockchain',
    'project',
    'version',
    'block_date',
    'project_contract_address',
    'gauge_address',
    'pool_symbol',
    'pool_type',
    'swap_amount_usd',
    'tvl_usd',
    'tvl_eth',
    'total_protocol_fee_usd',
    'protocol_fee_amount_usd',
    'swap_fee_usd',
    'yield_fee_usd',
    'swap_fee_%',
    'core_non_core',
    'bal_emited_votes',
    'votes_received',
    'bribe_amount_usd'
]


def create_final_dataset(
    vebal_file: Path = VEBAL_FILE,
    votes_bribes_file: Path = VOTES_BRIBES_FILE,
    core_pools_classification_file: Path = CORE_POOLS_CLASSIFICATION_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Creates the final dataset by combining veBAL.csv, core pools classification, 
    and votes_bribes_merged.csv.
    
    The function performs:
    1. Merge veBAL with core pools classification (using first 42 chars of address)
    2. Left merge on gauge_address, block_date, and blockchain with votes_bribes
    
    Rows from veBAL where gauge_address is missing or invalid are removed before merging.
    The final dataset is sorted by block_date (descending), blockchain, and 
    project_contract_address.
    
    Args:
        vebal_file: Path to veBAL CSV file
        votes_bribes_file: Path to votes_bribes_merged CSV file
        core_pools_classification_file: Path to core pools classification CSV file
        output_file: Path to output CSV file
        
    Returns:
        DataFrame with the final dataset containing all columns specified in FINAL_COLUMNS
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    print("=" * 60)
    print("🎯 Creating Final Dataset - Balancer All Tokenomics")
    print("=" * 60)
    
    if not vebal_file.exists():
        raise FileNotFoundError(f"File not found: {vebal_file}")
    if not votes_bribes_file.exists():
        raise FileNotFoundError(f"File not found: {votes_bribes_file}")
    if not core_pools_classification_file.exists():
        raise FileNotFoundError(f"File not found: {core_pools_classification_file}")
    
    print("\n📖 Reading files...")
    
    vebal_df = pd.read_csv(vebal_file)
    votes_bribes_df = pd.read_csv(votes_bribes_file)
    core_pools_df = pd.read_csv(core_pools_classification_file)
    
    print(f"✅ veBAL CSV: {len(vebal_df):,} rows")
    print(f"   Columns: {list(vebal_df.columns)}")
    print(f"✅ Votes_Bribes CSV: {len(votes_bribes_df):,} rows")
    print(f"   Columns: {list(votes_bribes_df.columns)}")
    print(f"✅ Core Pools Classification CSV: {len(core_pools_df):,} rows")
    print(f"   Columns: {list(core_pools_df.columns)}")
    
    required_vebal_cols = ['block_date', 'project_contract_address', 'gauge_address', 'blockchain']
    missing_vebal = [col for col in required_vebal_cols if col not in vebal_df.columns]
    
    if missing_vebal:
        raise ValueError(f"Missing columns in veBAL: {missing_vebal}")
    
    if 'day' not in votes_bribes_df.columns and 'block_date' not in votes_bribes_df.columns:
        raise ValueError("Column 'day' or 'block_date' not found in votes_bribes_merged")
    
    print("\n🧹 Cleaning and preparing data...")
    
    # Keep all rows - don't filter by gauge_address
    # Users can filter by gauge_address presence in the Streamlit UI
    initial_vebal = len(vebal_df)
    print(f"✅ veBAL after cleaning: {len(vebal_df):,} rows (all rows kept, including those without gauge_address)")
    
    # Define timezone removal function FIRST
    def remove_timezone(series):
        """Removes timezone from a datetime series if it exists."""
        try:
            if hasattr(series.dt, 'tz') and series.dt.tz is not None:
                return series.dt.tz_localize(None)
        except (AttributeError, TypeError):
            pass
        return series
    
    print("\n🔗 Converting and normalizing dates...")
    
    # Convert veBAL dates and remove timezone
    vebal_df['block_date'] = pd.to_datetime(vebal_df['block_date'], errors='coerce', utc=True)
    vebal_df['block_date'] = remove_timezone(vebal_df['block_date'])
    
    # Convert core pools dates and remove timezone
    core_pools_df['day'] = pd.to_datetime(core_pools_df['day'], errors='coerce')
    core_pools_df['day'] = remove_timezone(core_pools_df['day'])
    
    print("   ✅ Dates converted to timezone-naive datetime")
    
    print("\n🔗 Merging Core Pools classification with veBAL...")
    
    vebal_df['address_42'] = vebal_df['project_contract_address'].astype(str).str[:42].str.lower().str.strip()
    core_pools_df['address_42'] = core_pools_df['address'].astype(str).str[:42].str.lower().str.strip()
    
    core_pools_df = core_pools_df.rename(columns={'day': 'block_date'})
    
    vebal_df = vebal_df.merge(
        core_pools_df[['address_42', 'block_date', 'is_core']],
        on=['address_42', 'block_date'],
        how='left'
    )
    
    vebal_df['is_core'] = vebal_df['is_core'].fillna(False).astype(bool)
    
    vebal_df = vebal_df.drop(columns=['address_42'])
    
    core_matched = vebal_df['is_core'].sum()
    core_not_matched = len(vebal_df) - core_matched
    print(f"✅ Core pools classification merged:")
    print(f"   Core pools: {core_matched:,} ({100 * core_matched / len(vebal_df):.2f}%)")
    print(f"   Non-core pools: {core_not_matched:,} ({100 * core_not_matched / len(vebal_df):.2f}%)")
    
    # Convert votes_bribes dates and ensure timezone-naive
    if 'day' in votes_bribes_df.columns:
        # Force UTC conversion then remove timezone to match veBAL format
        votes_bribes_df['day'] = pd.to_datetime(votes_bribes_df['day'], errors='coerce', utc=True)
        votes_bribes_df['day'] = remove_timezone(votes_bribes_df['day'])
        date_col_bribes = 'day'
    else:
        votes_bribes_df['block_date'] = pd.to_datetime(votes_bribes_df['block_date'], errors='coerce', utc=True)
        votes_bribes_df['block_date'] = remove_timezone(votes_bribes_df['block_date'])
        date_col_bribes = 'block_date'
    
    print("   ✅ All dates standardized (timezone-naive datetime64[ns])")
    
    vebal_df['gauge_address'] = vebal_df['gauge_address'].astype(str).str.lower().str.strip()
    vebal_df['blockchain'] = vebal_df['blockchain'].astype(str).str.lower().str.strip()
    
    votes_bribes_df['gauge_address'] = votes_bribes_df['gauge_address'].astype(str).str.lower().str.strip()
    if 'blockchain' in votes_bribes_df.columns:
        votes_bribes_df['blockchain'] = votes_bribes_df['blockchain'].astype(str).str.lower().str.strip()
    
    initial_votes_bribes = len(votes_bribes_df)
    votes_bribes_df = votes_bribes_df[
        votes_bribes_df['gauge_address'].notna() & 
        (votes_bribes_df['gauge_address'] != '') &
        (votes_bribes_df['gauge_address'].astype(str).str.lower() != 'nan') &
        votes_bribes_df[date_col_bribes].notna()
    ]
    if len(votes_bribes_df) < initial_votes_bribes:
        print(f"   Removed {initial_votes_bribes - len(votes_bribes_df):,} invalid rows from votes_bribes_merged")
    
    print(f"✅ Votes_Bribes after cleaning: {len(votes_bribes_df):,} rows")
    
    if date_col_bribes == 'day':
        votes_bribes_df = votes_bribes_df.rename(columns={'day': 'block_date'})
    
    # CRITICAL FIX: Remove overlapping columns from veBAL that will be filled from votes_bribes
    print("\n🧹 Removing empty columns from veBAL that will be filled from votes_bribes...")
    cols_to_remove = []
    for col in ['bal_emited_votes', 'votes_received', 'core_non_core']:
        if col in vebal_df.columns:
            cols_to_remove.append(col)
            print(f"   Removing: {col} (will be filled from votes_bribes or classification)")
    
    if cols_to_remove:
        vebal_df = vebal_df.drop(columns=cols_to_remove)
    
    print("\n🔗 Merging data...")
    print("   Match keys: gauge_address, block_date, blockchain")
    
    merged_df = pd.merge(
        vebal_df,
        votes_bribes_df,
        on=['gauge_address', 'block_date', 'blockchain'],
        how='left',
        suffixes=('', '_votes_bribes')
    )
    
    print(f"✅ Merge completed: {len(merged_df):,} rows")
    
    matched_count = merged_df['bal_emited_votes'].notna().sum() if 'bal_emited_votes' in merged_df.columns else 0
    unmatched_count = len(merged_df) - matched_count
    
    print(f"\n📊 Merge statistics:")
    print(f"   Total rows: {len(merged_df):,}")
    print(f"   Rows with votes/bribes data: {matched_count:,} ({100 * matched_count / len(merged_df):.2f}%)")
    print(f"   Rows without votes/bribes data: {unmatched_count:,} ({100 * unmatched_count / len(merged_df):.2f}%)")
    
    print("\n📋 Preparing final columns...")
    
    final_df = pd.DataFrame()
    
    for col in FINAL_COLUMNS:
        col_found = None
        if col in merged_df.columns:
            col_found = col
        else:
            for merged_col in merged_df.columns:
                if merged_col.startswith(col) and not merged_col.endswith('_votes_bribes'):
                    col_found = merged_col
                    break
        
        if col_found:
            final_df[col] = merged_df[col_found]
        elif col == 'swap_fee_%':
            swap_fee_col = None
            swap_amount_col = None
            
            for c in merged_df.columns:
                if 'swap_fee_usd' in c.lower() and not c.endswith('_votes_bribes'):
                    swap_fee_col = c
                if 'swap_amount_usd' in c.lower() and not c.endswith('_votes_bribes'):
                    swap_amount_col = c
            
            if swap_fee_col and swap_amount_col:
                final_df[col] = (merged_df[swap_fee_col] / merged_df[swap_amount_col] * 100).fillna(0)
                print(f"   Calculated: {col} from {swap_fee_col} and {swap_amount_col}")
            else:
                final_df[col] = 0
                print(f"   ⚠️  Could not calculate {col} - columns not found")
        elif col == 'core_non_core':
            if 'is_core' in merged_df.columns:
                final_df[col] = merged_df['is_core']
                print(f"   ✅ Mapped: {col} from is_core column")
            else:
                final_df[col] = None
                print(f"   ⚠️  Column not found: is_core - {col} created as empty")
        else:
            final_df[col] = None
            print(f"   ⚠️  Column not found: {col} - created as empty")
    
    initial_count = len(final_df)
    final_df = final_df.drop_duplicates()
    if len(final_df) < initial_count:
        print(f"\n🧹 Removed {initial_count - len(final_df):,} duplicates")
    
    final_df = final_df.sort_values(['block_date', 'blockchain', 'project_contract_address'], ascending=[False, True, True], na_position='last')
    
    print(f"\n📊 Final statistics:")
    print(f"   Total rows: {len(final_df):,}")
    print(f"   Total columns: {len(final_df.columns)}")
    print(f"   Unique pools: {final_df['project_contract_address'].nunique():,}")
    print(f"   Unique gauge addresses: {final_df['gauge_address'].nunique():,}")
    
    if 'bribe_amount_usd' in final_df.columns:
        total_bribes = final_df['bribe_amount_usd'].sum()
        print(f"   Total bribes: {total_bribes:,.2f} USD")
    
    if 'bal_emited_votes' in final_df.columns:
        total_emissions = final_df['bal_emited_votes'].sum()
        print(f"   Total BAL emitted: {total_emissions:,.2f}")
    
    print(f"\n💾 Saving result to {output_file}...")
    final_df.to_csv(output_file, index=False)
    
    print(f"✅ File saved successfully!")
    
    print(f"\n📋 Data sample (first 10 rows):")
    print(final_df.head(10).to_string(index=False))
    
    print(f"\n📊 Column information:")
    for col in FINAL_COLUMNS:
        if col in final_df.columns:
            non_null = final_df[col].notna().sum()
            null_count = len(final_df) - non_null
            pct = 100 * non_null / len(final_df) if len(final_df) > 0 else 0
            print(f"   {col}: {non_null:,} values ({pct:.1f}% filled)")
    
    return final_df


def main():
    """
    Main function to execute the final dataset creation process.
    
    Returns:
        DataFrame with the final dataset containing all columns specified in FINAL_COLUMNS
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    try:
        result_df = create_final_dataset()
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
