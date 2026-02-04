#!/usr/bin/env python3
"""
Script to merge Votes_Emissions.csv and Bribes_enriched.csv

Match keys:
- gauge_address
- day
- blockchain

Renames:
- amount_usdc (Bribes) → bribe_amount_usd
- daily_emissions (Votes_Emissions) → bal_emited_votes
- total_votes (Votes_Emissions) → votes_received

IMPORTANT: Uses Bribes_enriched.csv (not Bribes.csv) which has:
- Metadata from HiddenHand
- gauge_address filled from FSN_data
- blockchain filled from FSN_data
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

VOTES_EMISSIONS_FILE = DATA_DIR / "Votes_Emissions.csv"
BRIBES_FILE = DATA_DIR / "Bribes_enriched.csv"
OUTPUT_FILE = DATA_DIR / "votes_bribes_merged.csv"


def merge_votes_bribes(
    votes_file: Path = VOTES_EMISSIONS_FILE,
    bribes_file: Path = BRIBES_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Merges Votes_Emissions.csv and Bribes_enriched.csv.
    
    Uses Bribes_enriched.csv (NOT Bribes.csv) which contains:
    - Original Dune bribe data
    - HiddenHand metadata
    - gauge_address filled from FSN_data
    - blockchain filled from FSN_data
    
    Performs an outer merge on gauge_address, day, and blockchain. If multiple
    bribes exist for the same (gauge_address, day, blockchain) combination,
    they are aggregated by summing the bribe_amount_usd values.
    
    Column renames:
    - amount_usdc → bribe_amount_usd
    - daily_emissions → bal_emited_votes
    - total_votes → votes_received
    
    Args:
        votes_file: Path to Votes_Emissions CSV file
        bribes_file: Path to Bribes_enriched CSV file
        output_file: Path to output CSV file
        
    Returns:
        DataFrame with merged data containing all records from both sources
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    print("=" * 60)
    print("🔗 Merging Votes_Emissions and Bribes")
    print("=" * 60)
    
    if not votes_file.exists():
        raise FileNotFoundError(f"File not found: {votes_file}")
    if not bribes_file.exists():
        raise FileNotFoundError(f"File not found: {bribes_file}")
    
    print("\n📖 Reading files...")
    
    votes_df = pd.read_csv(votes_file)
    bribes_df = pd.read_csv(bribes_file)
    
    print(f"✅ Votes_Emissions CSV: {len(votes_df):,} rows")
    print(f"   Columns: {list(votes_df.columns)}")
    print(f"✅ Bribes_enriched CSV: {len(bribes_df):,} rows")
    print(f"   Columns: {list(bribes_df.columns)}")
    
    required_votes_cols = ['gauge_address', 'day', 'blockchain']
    required_bribes_cols = ['gauge_address', 'day', 'blockchain']
    
    missing_votes = [col for col in required_votes_cols if col not in votes_df.columns]
    missing_bribes = [col for col in required_bribes_cols if col not in bribes_df.columns]
    
    if missing_votes:
        raise ValueError(f"Missing columns in Votes_Emissions: {missing_votes}")
    if missing_bribes:
        raise ValueError(f"Missing columns in Bribes: {missing_bribes}")
    
    print("\n🧹 Cleaning and preparing data...")
    
    votes_df['day'] = pd.to_datetime(votes_df['day'], errors='coerce')
    bribes_df['day'] = pd.to_datetime(bribes_df['day'], errors='coerce')
    
    # Remove timezone to ensure compatibility
    def remove_timezone(series):
        """Removes timezone from a datetime series if it exists."""
        try:
            if hasattr(series.dt, 'tz') and series.dt.tz is not None:
                return series.dt.tz_localize(None)
        except (AttributeError, TypeError):
            pass
        return series
    
    votes_df['day'] = remove_timezone(votes_df['day'])
    bribes_df['day'] = remove_timezone(bribes_df['day'])
    
    print("   ✅ Dates standardized (timezone removed)")
    
    votes_df['gauge_address'] = votes_df['gauge_address'].astype(str).str.lower().str.strip()
    votes_df['blockchain'] = votes_df['blockchain'].astype(str).str.lower().str.strip()
    
    bribes_df['gauge_address'] = bribes_df['gauge_address'].astype(str).str.lower().str.strip()
    bribes_df['blockchain'] = bribes_df['blockchain'].astype(str).str.lower().str.strip()
    
    initial_votes = len(votes_df)
    votes_df = votes_df[
        votes_df['gauge_address'].notna() & 
        (votes_df['gauge_address'] != '') &
        (votes_df['gauge_address'].str.lower() != 'nan') &
        votes_df['day'].notna() &
        votes_df['blockchain'].notna() &
        (votes_df['blockchain'] != '')
    ]
    if len(votes_df) < initial_votes:
        print(f"   Removed {initial_votes - len(votes_df):,} invalid rows from Votes_Emissions")
    
    initial_bribes = len(bribes_df)
    bribes_df = bribes_df[
        bribes_df['gauge_address'].notna() & 
        (bribes_df['gauge_address'] != '') &
        (bribes_df['gauge_address'].str.lower() != 'nan') &
        bribes_df['day'].notna() &
        bribes_df['blockchain'].notna() &
        (bribes_df['blockchain'] != '')
    ]
    if len(bribes_df) < initial_bribes:
        print(f"   Removed {initial_bribes - len(bribes_df):,} invalid rows from Bribes")
    
    print(f"✅ Votes_Emissions after cleaning: {len(votes_df):,} rows")
    print(f"✅ Bribes after cleaning: {len(bribes_df):,} rows")
    
    print("\n🔄 Renaming columns...")
    
    bribes_renamed = bribes_df.rename(columns={
        'amount_usdc': 'bribe_amount_usd'
    })
    
    votes_renamed = votes_df.rename(columns={
        'daily_emissions': 'bal_emited_votes',
        'total_votes': 'votes_received'
    })
    
    print("   Bribes: amount_usdc → bribe_amount_usd")
    print("   Votes_Emissions: daily_emissions → bal_emited_votes")
    print("   Votes_Emissions: total_votes → votes_received")
    
    print("\n🔗 Merging data...")
    print("   Match keys: gauge_address, day, blockchain")
    
    merged_df = pd.merge(
        votes_renamed,
        bribes_renamed,
        on=['gauge_address', 'day', 'blockchain'],
        how='outer',
        suffixes=('_votes', '_bribes'),
        indicator=True
    )
    
    merged_df['source'] = merged_df['_merge'].map({
        'left_only': 'votes_only',
        'right_only': 'bribes_only',
        'both': 'both'
    })
    merged_df = merged_df.drop(columns=['_merge'])
    
    print(f"✅ Merge completed: {len(merged_df):,} rows")
    
    print(f"\n📊 Merge statistics:")
    print(f"   Total rows after merge: {len(merged_df):,}")
    print(f"   Rows only in Votes_Emissions: {(merged_df['source'] == 'votes_only').sum():,}")
    print(f"   Rows only in Bribes: {(merged_df['source'] == 'bribes_only').sum():,}")
    print(f"   Rows in both (match): {(merged_df['source'] == 'both').sum():,}")
    
    matched_gauges = merged_df[merged_df['source'] == 'both']['gauge_address'].nunique()
    total_gauges_votes = votes_df['gauge_address'].nunique()
    total_gauges_bribes = bribes_df['gauge_address'].nunique()
    
    print(f"\n   Unique gauge addresses:")
    print(f"     In Votes_Emissions: {total_gauges_votes:,}")
    print(f"     In Bribes: {total_gauges_bribes:,}")
    print(f"     With match: {matched_gauges:,}")
    
    if 'bribe_amount_usd' in merged_df.columns:
        duplicates_check = merged_df[
            (merged_df['source'] == 'both') & 
            merged_df.duplicated(subset=['gauge_address', 'day', 'blockchain'], keep=False)
        ]
        if len(duplicates_check) > 0:
            print(f"\n⚠️  Warning: {len(duplicates_check):,} rows have multiple records for the same (gauge_address, day, blockchain)")
            print("   This may indicate multiple bribes on the same day. Checking...")
            
            print("   Grouping and summing duplicate bribes...")
            
            votes_cols = [col for col in merged_df.columns if col.endswith('_votes') or col in ['gauge_address', 'day', 'blockchain', 'source']]
            bribes_cols = [col for col in merged_df.columns if col.endswith('_bribes') or col == 'bribe_amount_usd']
            
            matched_rows = merged_df[merged_df['source'] == 'both'].copy()
            
            agg_dict = {}
            for col in matched_rows.columns:
                if col in ['gauge_address', 'day', 'blockchain']:
                    agg_dict[col] = 'first'
                elif col == 'bribe_amount_usd':
                    agg_dict[col] = 'sum'
                elif col.endswith('_votes'):
                    agg_dict[col] = 'first'
                elif col.endswith('_bribes') and col != 'bribe_amount_usd':
                    agg_dict[col] = 'first'
                elif col == 'source':
                    agg_dict[col] = 'first'
                else:
                    agg_dict[col] = 'first'
            
            matched_grouped = matched_rows.groupby(['gauge_address', 'day', 'blockchain']).agg(agg_dict).reset_index()
            
            votes_only = merged_df[merged_df['source'] == 'votes_only']
            bribes_only = merged_df[merged_df['source'] == 'bribes_only']
            
            merged_df = pd.concat([matched_grouped, votes_only, bribes_only], ignore_index=True)
            
            print(f"   After grouping: {len(merged_df):,} rows")
    
    merged_df = merged_df.sort_values(['day', 'blockchain', 'gauge_address'], na_position='last')
    
    print(f"\n💾 Saving result to {output_file}...")
    merged_df.to_csv(output_file, index=False)
    
    print(f"✅ File saved successfully!")
    print(f"   Total rows: {len(merged_df):,}")
    print(f"   Total columns: {len(merged_df.columns)}")
    
    print(f"\n📋 Data sample (first 10 rows with match):")
    sample = merged_df[merged_df['source'] == 'both'].head(10)
    if len(sample) > 0:
        cols_to_show = ['day', 'blockchain', 'gauge_address', 'bal_emited_votes', 'votes_received', 'bribe_amount_usd']
        available_cols = [col for col in cols_to_show if col in sample.columns]
        print(sample[available_cols].to_string(index=False))
    else:
        print("   No rows with match found to display")
    
    print(f"\n📊 Final statistics:")
    if 'bribe_amount_usd' in merged_df.columns:
        total_bribes = merged_df['bribe_amount_usd'].sum()
        print(f"   Total bribes (sum): {total_bribes:,.2f} USD")
    
    if 'bal_emited_votes' in merged_df.columns:
        total_emissions = merged_df['bal_emited_votes'].sum()
        print(f"   Total BAL emitted (sum): {total_emissions:,.2f}")
    
    if 'votes_received' in merged_df.columns:
        total_votes = merged_df['votes_received'].sum()
        print(f"   Total votes (sum): {total_votes:,.2f}")
    
    return merged_df


def main():
    """
    Main function to execute the votes and bribes merge process.
    
    Returns:
        DataFrame with merged votes and bribes data
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If required columns are missing
    """
    try:
        result_df = merge_votes_bribes()
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
