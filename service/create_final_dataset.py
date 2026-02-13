#!/usr/bin/env python3
"""
Script to create the final dataset by combining veBAL.csv and votes_bribes_merged.csv

Strategy:
1. Standardize all join keys (lowercase, stripped, timezone-naive).
2. Perform a multi-stage merge to ensure no data loss:
   - Stage 1: Match by gauge_address + block_date + blockchain
   - Stage 2: For unmatched rows, match by pool_address + block_date + blockchain
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

VEBAL_FILE = DATA_DIR / "veBAL.csv"
VOTES_BRIBES_FILE = DATA_DIR / "votes_bribes_merged.csv"
CORE_POOLS_CLASSIFICATION_FILE = DATA_DIR / "classification_core_pools.csv"
HIDDENHAND_BRIBES_FILE = DATA_DIR / "hiddenhand_bribes.csv"
OUTPUT_FILE_ALL = DATA_DIR / "Balancer-All-Tokenomics.csv"
OUTPUT_FILE_ORGANIZED = DATA_DIR / "Balancer-All-Tokenomics-Organized.csv"
DEBUG_UNMATCHED_FINAL = DATA_DIR / "bribes_unmatched_in_final.csv"

FINAL_COLUMNS = [
    'blockchain', 'project', 'version', 'block_date', 'project_contract_address',
    'gauge_address', 'has_gauge', 'pool_symbol', 'pool_type', 'swap_amount_usd',
    'tvl_usd', 'tvl_eth', 'total_protocol_fee_usd', 'protocol_fee_amount_usd',
    'swap_fee_usd', 'yield_fee_usd', 'swap_fee_percent', 'core_non_core',
    'bal_emited_votes', 'bal_emited_usd', 'votes_received', 'bribe_amount_usd'
]

def create_final_dataset():
    print("=" * 60)
    print("🎯 Creating Final Dataset - Robust Merge")
    print("=" * 60)
    
    print("\n📖 Reading files...")
    vebal_df = pd.read_csv(VEBAL_FILE)
    vb_df = pd.read_csv(VOTES_BRIBES_FILE)
    core_df = pd.read_csv(CORE_POOLS_CLASSIFICATION_FILE)
    hiddenhand_df = pd.read_csv(HIDDENHAND_BRIBES_FILE)
    
    print("🧹 Standardizing veBAL...")
    vebal_df['gauge_key'] = vebal_df['gauge_address'].fillna('').astype(str).str.lower().str.strip()
    vebal_df['pool_key'] = vebal_df['project_contract_address'].astype(str).str.lower().str.strip().str[:42]
    vebal_df['date_key'] = pd.to_datetime(vebal_df['block_date']).dt.tz_localize(None)
    vebal_df['chain_key'] = vebal_df['blockchain'].astype(str).str.lower().str.strip()
    
    for col in ['bal_emited_votes', 'votes_received', 'bribe_amount_usd', 'core_non_core']:
        if col in vebal_df.columns:
            vebal_df = vebal_df.drop(columns=[col])

    print("🧹 Standardizing Votes/Bribes...")
    vb_df['gauge_key'] = vb_df['gauge_address'].fillna('').astype(str).str.lower().str.strip()
    if 'pool_42' not in vb_df.columns:
        def _pool_42_from_row(row):
            for col in ['pool_id', 'derived_pool_address', 'pool_address']:
                val = row.get(col)
                if pd.notna(val) and str(val).strip() != '':
                    return str(val).strip().lower()[:42]
            return ''
        vb_df['pool_42'] = vb_df.apply(_pool_42_from_row, axis=1)
    vb_df['pool_key'] = vb_df['pool_42'].fillna('').astype(str).str.lower().str.strip()
    vb_df['date_key'] = pd.to_datetime(vb_df['day']).dt.tz_localize(None)
    vb_df['chain_key'] = vb_df['blockchain'].astype(str).str.lower().str.strip()

    print("\n🔗 Stage 1: Matching by Gauge...")
    vb_gauge = vb_df.groupby(['gauge_key', 'date_key', 'chain_key']).agg({
        'bribe_amount_usd': 'sum',
        'bal_emited_votes': 'sum',
        'bal_emited_usd': 'sum',
        'votes_received': 'sum'
    }).reset_index()
    
    merged_df = pd.merge(
        vebal_df,
        vb_gauge,
        on=['gauge_key', 'date_key', 'chain_key'],
        how='left'
    )
    
    print(f"   ✅ Bribes matched by gauge: ${merged_df['bribe_amount_usd'].sum():,.2f}")

    print("🔗 Stage 2: Matching by Pool (Fallback)...")
    still_unmatched_mask = merged_df['bribe_amount_usd'].isna() | (merged_df['bribe_amount_usd'] == 0)
    
    if still_unmatched_mask.any():
        vb_pool = vb_df[vb_df['bribe_amount_usd'] > 0].groupby(['pool_key', 'date_key', 'chain_key']).agg({
            'bribe_amount_usd': 'sum',
            'bal_emited_votes': 'sum',
            'bal_emited_usd': 'sum',
            'votes_received': 'sum'
        }).reset_index()
        
        pool_matches = pd.merge(
            merged_df[still_unmatched_mask][['pool_key', 'date_key', 'chain_key']].reset_index(),
            vb_pool,
            on=['pool_key', 'date_key', 'chain_key'],
            how='inner'
        )
        
        if len(pool_matches) > 0:
            match_data = pool_matches.set_index('index')
            merged_df.loc[match_data.index, 'bribe_amount_usd'] = match_data['bribe_amount_usd']
            merged_df.loc[match_data.index, 'bal_emited_votes'] = match_data['bal_emited_votes']
            merged_df.loc[match_data.index, 'bal_emited_usd'] = match_data['bal_emited_usd']
            merged_df.loc[match_data.index, 'votes_received'] = match_data['votes_received']
            print(f"   ✅ Additional bribes matched by pool: ${pool_matches['bribe_amount_usd'].sum():,.2f}")

    print("🛡️ Adding Core Pools classification...")
    core_df['pool_key'] = core_df['address'].astype(str).str.lower().str.strip().str[:42]
    core_df['date_key'] = pd.to_datetime(core_df['day']).dt.tz_localize(None)
    
    merged_df = pd.merge(
        merged_df,
        core_df[['pool_key', 'date_key', 'is_core']],
        on=['pool_key', 'date_key'],
        how='left'
    )
    merged_df['core_non_core'] = merged_df['is_core'].fillna(False)

    print("🧩 Filling missing pool_symbol from HiddenHand...")
    hiddenhand_df['pool_key'] = hiddenhand_df['pool_id'].astype(str).str.lower().str.strip().str[:42]
    hiddenhand_map = hiddenhand_df.groupby('pool_key')['pool_name'].first().to_dict()
    missing_pool_symbol = merged_df['pool_symbol'].isna() | (merged_df['pool_symbol'].astype(str).str.strip() == '')
    merged_df.loc[missing_pool_symbol, 'pool_symbol'] = merged_df.loc[missing_pool_symbol, 'pool_key'].map(hiddenhand_map)

    print("🧹 Finalizing columns...")
    if 'swap_fee_%' in merged_df.columns and 'swap_fee_percent' not in merged_df.columns:
        merged_df = merged_df.rename(columns={'swap_fee_%': 'swap_fee_percent'})
    merged_df['has_gauge'] = (merged_df['gauge_address'].notna()) & (merged_df['gauge_address'].astype(str) != 'nan') & (merged_df['gauge_address'] != '')

    vebal_gauge_keys = set(zip(vebal_df['gauge_key'], vebal_df['date_key'], vebal_df['chain_key']))
    vebal_pool_keys = set(zip(vebal_df['pool_key'], vebal_df['date_key'], vebal_df['chain_key']))

    vb_with_bribes = vb_df[(vb_df['bribe_amount_usd'] > 0) & vb_df['date_key'].notna()].copy()
    vb_with_bribes['match_by_gauge'] = vb_with_bribes.apply(
        lambda r: (r['gauge_key'], r['date_key'], r['chain_key']) in vebal_gauge_keys, axis=1
    )
    vb_with_bribes['match_by_pool'] = vb_with_bribes.apply(
        lambda r: (r['pool_key'], r['date_key'], r['chain_key']) in vebal_pool_keys, axis=1
    )
    vb_unmatched_final = vb_with_bribes[~(vb_with_bribes['match_by_gauge'] | vb_with_bribes['match_by_pool'])].copy()
    if len(vb_unmatched_final) > 0:
        debug_cols = [
            'day', 'blockchain', 'gauge_address', 'pool_42', 'bribe_amount_usd',
            'match_by_gauge', 'match_by_pool'
        ]
        available_debug_cols = [c for c in debug_cols if c in vb_unmatched_final.columns]
        vb_unmatched_final[available_debug_cols].to_csv(DEBUG_UNMATCHED_FINAL, index=False)
        print(f"🧾 Debug file written: {DEBUG_UNMATCHED_FINAL}")
        print(f"   Unmatched bribes in final: {len(vb_unmatched_final):,}")
    
    for col in FINAL_COLUMNS:
        if col not in merged_df.columns:
            merged_df[col] = None

    final_df = merged_df[FINAL_COLUMNS].drop_duplicates()
    final_df = final_df.sort_values(['block_date', 'blockchain'], ascending=[False, True])

    print(f"\n📊 TOTAL BRIBES MATCHED: ${final_df['bribe_amount_usd'].sum():,.2f}")
    
    final_df.to_csv(OUTPUT_FILE_ALL, index=False)
    organized_df = final_df[
        (final_df['bribe_amount_usd'] > 0) | 
        (final_df['bal_emited_votes'] > 0)
    ].copy()
    organized_df.to_csv(OUTPUT_FILE_ORGANIZED, index=False)
    
    print(f"✅ Saved {len(final_df):,} rows to ALL version")
    print(f"✅ Saved {len(organized_df):,} rows to ORGANIZED version")
    
    return final_df


def main():
    """Main function to be called from main.py"""
    try:
        create_final_dataset()
        print("\n🚀 Process completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
