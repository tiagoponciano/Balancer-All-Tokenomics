#!/usr/bin/env python3
"""
Script to add gauge_address to veBAL.csv based on matching with FSN_data.csv.

Matching logic:
- Match between poolId (first 42 characters) from FSN_data.csv 
  and project_contract_address from veBAL.csv
- If the first 42 characters of poolId match project_contract_address,
  adds the id (gauge_address) from FSN_data.csv to veBAL.csv
"""
import pandas as pd
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

VEBAL_FILE = DATA_DIR / "veBAL.csv"
FSN_DATA_FILE = DATA_DIR / "FSN_data.csv"
OUTPUT_FILE = DATA_DIR / "veBAL.csv"


def add_gauge_address(
    vebal_file: Path = VEBAL_FILE,
    fsn_data_file: Path = FSN_DATA_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Adds gauge_address to veBAL.csv based on matching with FSN_data.csv.
    
    The function matches pools by comparing the first 42 characters of poolId
    from FSN_data.csv with project_contract_address from veBAL.csv. When a match
    is found, the corresponding gauge_address (id) is added to the veBAL dataset.
    
    Args:
        vebal_file: Path to veBAL CSV file
        fsn_data_file: Path to FSN_data CSV file
        output_file: Path to output CSV file
        
    Returns:
        DataFrame with veBAL data including gauge_address column
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    print("=" * 60)
    print("🔗 Adding Gauge Address to veBAL")
    print("=" * 60)
    
    if not vebal_file.exists():
        raise FileNotFoundError(f"File not found: {vebal_file}")
    if not fsn_data_file.exists():
        raise FileNotFoundError(f"File not found: {fsn_data_file}")
    
    print("\n📖 Reading files...")
    
    vebal_df = pd.read_csv(vebal_file)
    print(f"✅ veBAL CSV: {len(vebal_df):,} rows")
    print(f"   Columns: {list(vebal_df.columns)}")
    
    if 'project_contract_address' not in vebal_df.columns:
        raise ValueError(
            f"Column 'project_contract_address' not found in veBAL. "
            f"Available columns: {list(vebal_df.columns)}"
        )
    
    fsn_df = pd.read_csv(fsn_data_file)
    print(f"✅ FSN_data CSV: {len(fsn_df):,} rows")
    print(f"   Columns: {list(fsn_df.columns)}")
    
    if 'id' not in fsn_df.columns:
        raise ValueError(
            f"Column 'id' not found in FSN_data. "
            f"Available columns: {list(fsn_df.columns)}"
        )
    if 'poolId' not in fsn_df.columns:
        raise ValueError(
            f"Column 'poolId' not found in FSN_data. "
            f"Available columns: {list(fsn_df.columns)}"
        )
    
    print("\n🧹 Cleaning and preparing data...")
    
    initial_fsn = len(fsn_df)
    fsn_df = fsn_df[fsn_df['poolId'].notna() & (fsn_df['poolId'] != '')]
    if len(fsn_df) < initial_fsn:
        print(f"   Removed {initial_fsn - len(fsn_df):,} rows with empty poolId from FSN_data")
    
    initial_vebal = len(vebal_df)
    vebal_df = vebal_df[vebal_df['project_contract_address'].notna() & (vebal_df['project_contract_address'] != '')]
    if len(vebal_df) < initial_vebal:
        print(f"   Removed {initial_vebal - len(vebal_df):,} rows with empty project_contract_address from veBAL")
    
    vebal_df['project_contract_address'] = vebal_df['project_contract_address'].astype(str).str.lower().str.strip()
    fsn_df['poolId'] = fsn_df['poolId'].astype(str).str.lower().str.strip()
    fsn_df['id'] = fsn_df['id'].astype(str).str.lower().str.strip()
    
    print("\n🔍 Creating match between datasets...")
    
    fsn_df['poolId_42'] = fsn_df['poolId'].str[:42]
    fsn_df = fsn_df[fsn_df['poolId_42'].str.len() >= 42]
    
    print(f"   FSN_data after processing: {len(fsn_df):,} rows")
    print(f"   Unique pools in FSN_data: {fsn_df['poolId_42'].nunique():,}")
    print(f"   Unique gauge addresses: {fsn_df['id'].nunique():,}")
    
    duplicates = fsn_df.groupby('poolId_42')['id'].nunique()
    duplicates = duplicates[duplicates > 1]
    if len(duplicates) > 0:
        print(f"\n⚠️  Warning: {len(duplicates)} pools have multiple gauge_addresses:")
        for pool_id, count in duplicates.head(10).items():
            gauges = fsn_df[fsn_df['poolId_42'] == pool_id]['id'].unique()
            print(f"   Pool {pool_id}: {count} gauges - {list(gauges)[:3]}")
        print("   Using the first gauge_address found for each pool")
    
    gauge_mapping = fsn_df.groupby('poolId_42')['id'].first().to_dict()
    
    print(f"\n📊 Mapping created: {len(gauge_mapping):,} pools mapped")
    
    print("\n🔄 Applying match to veBAL...")
    
    vebal_df['gauge_address'] = vebal_df['project_contract_address'].map(gauge_mapping)
    
    matched_count = vebal_df['gauge_address'].notna().sum()
    unmatched_count = len(vebal_df) - matched_count
    unique_pools_matched = vebal_df[vebal_df['gauge_address'].notna()]['project_contract_address'].nunique()
    unique_pools_total = vebal_df['project_contract_address'].nunique()
    
    print(f"\n📊 Match statistics:")
    print(f"   Total rows in veBAL: {len(vebal_df):,}")
    print(f"   Rows with gauge_address: {matched_count:,} ({100 * matched_count / len(vebal_df):.2f}%)")
    print(f"   Rows without gauge_address: {unmatched_count:,} ({100 * unmatched_count / len(vebal_df):.2f}%)")
    print(f"   Unique pools with match: {unique_pools_matched:,} / {unique_pools_total:,} ({100 * unique_pools_matched / unique_pools_total:.2f}%)")
    
    if unmatched_count > 0:
        unmatched_pools = vebal_df[vebal_df['gauge_address'].isna()]['project_contract_address'].unique()[:10]
        print(f"\n📋 Examples of pools without match (first 10):")
        for pool in unmatched_pools:
            print(f"   {pool}")
    
    print(f"\n💾 Saving result to {output_file}...")
    vebal_df.to_csv(output_file, index=False)
    
    print(f"✅ File saved successfully!")
    print(f"   Total rows: {len(vebal_df):,}")
    print(f"   Total columns: {len(vebal_df.columns)}")
    
    print(f"\n📋 Data sample (first 10 rows with gauge_address):")
    sample = vebal_df[vebal_df['gauge_address'].notna()].head(10)
    if len(sample) > 0:
        cols_to_show = ['project_contract_address', 'gauge_address', 'pool_symbol', 'block_date']
        available_cols = [col for col in cols_to_show if col in sample.columns]
        print(sample[available_cols].to_string(index=False))
    else:
        print("   No rows with gauge_address found to display")
    
    return vebal_df


def main():
    """
    Main function to execute the gauge address addition process.
    
    Returns:
        DataFrame with veBAL data including gauge_address column
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    try:
        result_df = add_gauge_address()
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
