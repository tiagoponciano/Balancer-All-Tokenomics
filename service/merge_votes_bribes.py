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
import ast
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

VOTES_EMISSIONS_FILE = DATA_DIR / "Votes_Emissions.csv"
BRIBES_FILE = DATA_DIR / "Bribes_enriched.csv"
FSN_DATA_FILE = DATA_DIR / "FSN_data.csv"
OUTPUT_FILE = DATA_DIR / "votes_bribes_merged.csv"
DEBUG_UNMATCHED_FILE = DATA_DIR / "bribes_unmatched_debug.csv"


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
    fsn_df = pd.read_csv(FSN_DATA_FILE)

    def parse_candidate_list(value):
        """Parse list/tuple-like strings into a list of gauge addresses."""
        if pd.isna(value):
            return None
        if isinstance(value, list):
            return value
        s = str(value).strip()
        if s == '':
            return None
        # Try to parse Python/JSON-like list/tuple strings
        if (s.startswith('[') and s.endswith(']')) or (s.startswith('(') and s.endswith(')')):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
            except (ValueError, SyntaxError):
                pass
        # Fallback: split on common delimiters
        if '|' in s or ';' in s or ',' in s:
            parts = [p.strip() for p in s.replace(';', '|').replace(',', '|').split('|') if p.strip()]
            if len(parts) > 1:
                return parts
        return None

    def explode_multi_gauges(df: pd.DataFrame, pool_to_gauges: dict) -> pd.DataFrame:
        """Explode rows that contain multiple gauge candidates."""
        if 'temp_row_id' not in df.columns:
            df = df.copy()
            df['temp_row_id'] = range(len(df))
        if 'is_derived_gauge' not in df.columns:
            df['is_derived_gauge'] = False

        exploded_rows = []
        for _, row in df.iterrows():
            candidates = parse_candidate_list(row.get('gauge_address'))
            if not candidates:
                pool_42 = None
                pool_id = row.get('pool_id')
                derived_pool = row.get('derived_pool_address')
                if pd.notna(pool_id) and str(pool_id).strip() != '':
                    pool_42 = str(pool_id).strip().lower()[:42]
                elif pd.notna(derived_pool) and str(derived_pool).strip() != '':
                    pool_42 = str(derived_pool).strip().lower()[:42]
                if pool_42 and pool_42 in pool_to_gauges:
                    candidates = pool_to_gauges[pool_42]

            if candidates and len(candidates) > 1:
                status_candidates = parse_candidate_list(row.get('gauge_status'))
                for i, candidate in enumerate(candidates):
                    new_row = row.copy()
                    new_row['gauge_address'] = candidate
                    if status_candidates and i < len(status_candidates):
                        new_row['gauge_status'] = status_candidates[i]
                    new_row['is_derived_gauge'] = True
                    exploded_rows.append(new_row)
            elif candidates and len(candidates) == 1:
                row['gauge_address'] = candidates[0]
                exploded_rows.append(row)
            else:
                exploded_rows.append(row)
        return pd.DataFrame(exploded_rows)

    # Build pool -> gauges mapping from FSN_data
    fsn_df['pool_42'] = fsn_df['poolId'].astype(str).str.lower().str.strip().str[:42]
    fsn_df['id_norm'] = fsn_df['id'].astype(str).str.lower().str.strip()
    pool_to_gauges = (
        fsn_df.groupby('pool_42')['id_norm']
        .apply(lambda s: sorted(set([x for x in s if x and x != 'nan'])))
        .to_dict()
    )

    bribes_df = explode_multi_gauges(bribes_df, pool_to_gauges)
    
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
    
    # --- FILTERING LOGIC FOR MULTIPLE GAUGES ---
    if 'is_derived_gauge' in merged_df.columns and 'temp_row_id' in merged_df.columns:
        print("\n🔍 Filtering speculative gauge matches...")
        initial_count = len(merged_df)
        
        # 1. Separate normal rows from speculative ones
        # speculative rows have is_derived_gauge == True (and thus a valid temp_row_id)
        # Note: merged_df['is_derived_gauge'] might contain NaNs for votes_only rows, treat as False
        is_speculative = merged_df['is_derived_gauge'].fillna(False).astype(bool)
        
        normal_rows = merged_df[~is_speculative]
        speculative_rows = merged_df[is_speculative]
        
        if len(speculative_rows) > 0:
            print(f"   Found {len(speculative_rows)} speculative rows to resolve.")
            
            # Group by temp_row_id to see which candidates matched
            # We want to keep rows that matched (source == 'both')
            # If multiple matched, keep all (or handle dupes later)
            # If none matched, keep a fallback (e.g. ACTIVE or first)
            
            resolved_rows = []
            
            # Group by temp_row_id
            for row_id, group in speculative_rows.groupby('temp_row_id'):
                matches = group[group['source'] == 'both']
                
                if len(matches) > 0:
                    # We found a match! Keep only the matched rows.
                    resolved_rows.append(matches)
                else:
                    # No match found for any candidate.
                    # We need to pick one to avoid duplication/data loss.
                    # Strategy: Prefer original gauge if available,
                    # then 'ACTIVE' status if available, else first one.

                    if 'gauge_address_original' in group.columns:
                        original = group['gauge_address_original'].dropna().astype(str).str.lower().str.strip()
                        if len(original) > 0:
                            original_value = original.iloc[0]
                            if original_value != '' and original_value != 'nan':
                                original_match = group[group['gauge_address'].astype(str).str.lower().str.strip() == original_value]
                                if len(original_match) > 0:
                                    resolved_rows.append(original_match.iloc[[0]])
                                    continue
                    
                    if 'gauge_status' in group.columns:
                        active = group[group['gauge_status'] == 'ACTIVE']
                        if len(active) > 0:
                            # Keep first active
                            resolved_rows.append(active.iloc[[0]])
                            continue
                            
                    # Fallback: keep the first candidate (arbitrary but consistent)
                    resolved_rows.append(group.iloc[[0]])
            
            if resolved_rows:
                resolved_df = pd.concat(resolved_rows, ignore_index=True)
                merged_df = pd.concat([normal_rows, resolved_df], ignore_index=True)
                print(f"   Resolved to {len(merged_df)} rows (removed {initial_count - len(merged_df)} speculative candidates)")
            else:
                 merged_df = normal_rows
        else:
            print("   No speculative rows found.")
            
    # Drop temp columns
    merged_df = merged_df.drop(columns=['is_derived_gauge', 'temp_row_id', 'gauge_status'], errors='ignore')
    # -------------------------------------------
    
    print(f"\n📊 Merge statistics:")
    print(f"   Total rows after merge: {len(merged_df):,}")
    print(f"   Rows only in Votes_Emissions: {(merged_df['source'] == 'votes_only').sum():,}")
    print(f"   Rows only in Bribes: {(merged_df['source'] == 'bribes_only').sum():,}")
    print(f"   Rows in both (match): {(merged_df['source'] == 'both').sum():,}")

    # Debug: export unmatched bribes to help identify data loss
    bribes_only = merged_df[merged_df['source'] == 'bribes_only'].copy()
    if len(bribes_only) > 0:
        def pool_candidate_count(row):
            pool_id = row.get('pool_id')
            derived_pool = row.get('derived_pool_address')
            pool_42 = None
            if pd.notna(pool_id) and str(pool_id).strip() != '':
                pool_42 = str(pool_id).strip().lower()[:42]
            elif pd.notna(derived_pool) and str(derived_pool).strip() != '':
                pool_42 = str(derived_pool).strip().lower()[:42]
            if pool_42 and pool_42 in pool_to_gauges:
                return len(pool_to_gauges[pool_42])
            return 0

        bribes_only['pool_candidate_gauges'] = bribes_only.apply(pool_candidate_count, axis=1)
        debug_cols = [
            'day', 'blockchain', 'pool_id', 'derived_pool_address',
            'pool_42', 'gauge_address', 'gauge_address_original',
            'bribe_amount_usd', 'pool_candidate_gauges'
        ]
        available_debug_cols = [c for c in debug_cols if c in bribes_only.columns]
        bribes_only[available_debug_cols].to_csv(DEBUG_UNMATCHED_FILE, index=False)
        print(f"\n🧾 Debug file written: {DEBUG_UNMATCHED_FILE}")
        print(f"   Unmatched bribes rows: {len(bribes_only):,}")
    
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
