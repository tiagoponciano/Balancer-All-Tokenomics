#!/usr/bin/env python3
"""
Script to combine bribe data from Dune (Bribes.csv) with HiddenHand data (hiddenhand_bribes.csv).

The script:
1. Reads both CSVs
2. Matches by proposal_hash
3. Identifies new pools from HiddenHand that are not in Bribes.csv
4. Combines data keeping all information
5. Saves as updated Bribes.csv
"""
import pandas as pd
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

DUNE_BRIBES_FILE = DATA_DIR / "Bribes.csv"
HIDDENHAND_BRIBES_FILE = DATA_DIR / "hiddenhand_bribes.csv"
OUTPUT_FILE = DATA_DIR / "Bribes.csv"


def merge_bribes_data(
    dune_file: Path = DUNE_BRIBES_FILE,
    hiddenhand_file: Path = HIDDENHAND_BRIBES_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Combines bribe data from Dune and HiddenHand by proposal_hash.
    
    Performs an outer merge to keep all records from both sources. If a proposal_hash
    exists in both sources, columns are suffixed with '_hiddenhand' and '_dune'.
    A 'source' column is added to indicate the origin of each record.
    
    Args:
        dune_file: Path to Dune CSV file
        hiddenhand_file: Path to HiddenHand CSV file
        output_file: Path to output CSV file
        
    Returns:
        DataFrame with combined data containing all records from both sources
        
    Raises:
        FileNotFoundError: If hiddenhand_file doesn't exist
        ValueError: If required columns are missing
    """
    print("=" * 60)
    print("🔄 Merging Bribes Data")
    print("=" * 60)
    
    if not hiddenhand_file.exists():
        raise FileNotFoundError(f"File not found: {hiddenhand_file}")
    
    print("\n📖 Reading files...")
    
    hiddenhand_df = pd.read_csv(hiddenhand_file)
    print(f"✅ HiddenHand CSV: {len(hiddenhand_df):,} rows")
    print(f"   Columns: {list(hiddenhand_df.columns)}")
    
    if 'proposal_hash' not in hiddenhand_df.columns:
        raise ValueError(
            f"Column 'proposal_hash' not found in HiddenHand file. "
            f"Available columns: {list(hiddenhand_df.columns)}"
        )
    
    dune_df = None
    if dune_file.exists():
        dune_df = pd.read_csv(dune_file)
        print(f"✅ Dune CSV: {len(dune_df):,} rows")
        print(f"   Columns: {list(dune_df.columns)}")
        
        if 'proposal_hash' not in dune_df.columns:
            print(f"⚠️  Column 'proposal_hash' not found in Dune file.")
            print(f"   Trying to find similar column...")
            
            proposal_cols = [col for col in dune_df.columns if 'proposal' in col.lower() or 'hash' in col.lower()]
            if proposal_cols:
                print(f"   Columns found: {proposal_cols}")
                dune_df = dune_df.rename(columns={proposal_cols[0]: 'proposal_hash'})
                print(f"   Column '{proposal_cols[0]}' renamed to 'proposal_hash'")
            else:
                print(f"⚠️  Could not find proposal_hash column in Dune.")
                print(f"   Continuing with HiddenHand data only...")
                dune_df = None
    else:
        print(f"⚠️  Dune file not found: {dune_file}")
        print(f"   Continuing with HiddenHand data only...")
    
    print("\n🧹 Cleaning data...")
    initial_hiddenhand = len(hiddenhand_df)
    hiddenhand_df = hiddenhand_df[hiddenhand_df['proposal_hash'].notna() & (hiddenhand_df['proposal_hash'] != '')]
    if len(hiddenhand_df) < initial_hiddenhand:
        print(f"   Removed {initial_hiddenhand - len(hiddenhand_df):,} rows with empty proposal_hash from HiddenHand")
    
    if dune_df is not None:
        initial_dune = len(dune_df)
        dune_df = dune_df[dune_df['proposal_hash'].notna() & (dune_df['proposal_hash'] != '')]
        if len(dune_df) < initial_dune:
            print(f"   Removed {initial_dune - len(dune_df):,} rows with empty proposal_hash from Dune")
    
    hiddenhand_df['proposal_hash'] = hiddenhand_df['proposal_hash'].astype(str).str.lower().str.strip()
    if dune_df is not None:
        dune_df['proposal_hash'] = dune_df['proposal_hash'].astype(str).str.lower().str.strip()
    
    print(f"\n📊 Initial statistics:")
    print(f"   HiddenHand: {len(hiddenhand_df):,} unique records by proposal_hash")
    unique_hiddenhand = hiddenhand_df['proposal_hash'].nunique()
    print(f"   HiddenHand: {unique_hiddenhand:,} unique proposal_hashes")
    
    if dune_df is not None:
        print(f"   Dune: {len(dune_df):,} unique records by proposal_hash")
        unique_dune = dune_df['proposal_hash'].nunique()
        print(f"   Dune: {unique_dune:,} unique proposal_hashes")
    
    print("\n🔗 Merging data...")
    
    if dune_df is not None:
        merged_df = pd.merge(
            hiddenhand_df,
            dune_df,
            on='proposal_hash',
            how='outer',
            suffixes=('_hiddenhand', '_dune'),
            indicator=True
        )
        
        merged_df['source'] = merged_df['_merge'].map({
            'left_only': 'hiddenhand_only',
            'right_only': 'dune_only',
            'both': 'both'
        })
        merged_df = merged_df.drop(columns=['_merge'])
        
        print(f"\n📊 Merge result:")
        print(f"   Total records after merge: {len(merged_df):,}")
        print(f"   Proposal_hashes only in HiddenHand: {(merged_df['source'] == 'hiddenhand_only').sum():,}")
        print(f"   Proposal_hashes only in Dune: {(merged_df['source'] == 'dune_only').sum():,}")
        print(f"   Proposal_hashes in both: {(merged_df['source'] == 'both').sum():,}")
        
        new_pools = merged_df[merged_df['source'] == 'hiddenhand_only']
        if len(new_pools) > 0:
            print(f"\n🆕 New pools found in HiddenHand: {len(new_pools):,}")
            if 'derived_pool_address' in new_pools.columns:
                unique_new_pools = new_pools['derived_pool_address'].nunique()
                print(f"   Unique pools (by address): {unique_new_pools:,}")
    else:
        merged_df = hiddenhand_df.copy()
        merged_df['source'] = 'hiddenhand_only'
        print(f"   Using HiddenHand data only: {len(merged_df):,} records")
    
    initial_count = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['proposal_hash'], keep='first')
    if len(merged_df) < initial_count:
        print(f"\n🧹 Removed {initial_count - len(merged_df):,} duplicates")
    
    date_cols = [col for col in merged_df.columns if 'date' in col.lower() or 'timestamp' in col.lower() or 'week' in col.lower()]
    if date_cols:
        sort_col = date_cols[0]
        merged_df = merged_df.sort_values(sort_col, ascending=False, na_position='last')
        print(f"   Sorted by: {sort_col}")
    else:
        merged_df = merged_df.sort_values('proposal_hash')
        print(f"   Sorted by: proposal_hash")
    
    print(f"\n💾 Saving result to {output_file}...")
    merged_df.to_csv(output_file, index=False)
    
    print(f"✅ File saved successfully!")
    print(f"   Total records: {len(merged_df):,}")
    print(f"   Total columns: {len(merged_df.columns)}")
    
    print(f"\n📋 Data sample (first 10 rows):")
    print(merged_df.head(10).to_string())
    
    print(f"\n📊 Final statistics:")
    print(f"   Total records: {len(merged_df):,}")
    print(f"   Unique proposal_hashes: {merged_df['proposal_hash'].nunique():,}")
    
    if 'derived_pool_address' in merged_df.columns:
        print(f"   Unique pools (by address): {merged_df['derived_pool_address'].nunique():,}")
    
    if 'source' in merged_df.columns:
        print(f"\n   Distribution by source:")
        source_counts = merged_df['source'].value_counts()
        for source, count in source_counts.items():
            print(f"     {source}: {count:,} ({100 * count / len(merged_df):.2f}%)")
    
    return merged_df


def main():
    """
    Main function to execute the bribe data merge process.
    
    Returns:
        DataFrame with combined bribe data from Dune and HiddenHand
        
    Raises:
        FileNotFoundError: If hiddenhand_file doesn't exist
        ValueError: If required columns are missing
    """
    try:
        result_df = merge_bribes_data()
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
