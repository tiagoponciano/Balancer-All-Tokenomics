#!/usr/bin/env python3
"""
Script to enrich Bribes_enriched.csv with missing blockchain and gauge_address from FSN_data.csv

Matching logic:
- Bidirectional matching: pool_id <-> gauge_address
- Use first 42 characters for matching (Ethereum address standard)
- Fill missing blockchain (chain), gauge_address (id), and pool_id where there's a match
- SUPPORT FOR MULTIPLE GAUGES: If a pool has multiple gauges, we store the candidate gauges
  as a list-like JSON string in gauge_address so downstream merge logic can resolve the match.
"""
import pandas as pd
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

BRIBES_ENRICHED_FILE = DATA_DIR / "Bribes_enriched.csv"
FSN_DATA_FILE = DATA_DIR / "FSN_data.csv"
OUTPUT_FILE = DATA_DIR / "Bribes_enriched.csv"


def normalize_address(addr):
    """Normalize address to lowercase and strip whitespace"""
    if pd.isna(addr) or addr == '':
        return None
    return str(addr).strip().lower()


def extract_base_address(address_str):
    """Extract first 42 characters (Ethereum address standard)"""
    if not address_str:
        return None
    addr = str(address_str).strip().lower()
    if addr.startswith('0x') and len(addr) >= 42:
        return addr[:42]
    return addr


def enrich_bribes_with_fsn():
    """
    Enriches Bribes_enriched.csv with missing blockchain, gauge_address, and pool_id from FSN_data.csv
    """
    print("=" * 70)
    print("Enriching Bribes with FSN Data (Bidirectional with Multi-Gauge Support)")
    print("=" * 70)
    
    if not BRIBES_ENRICHED_FILE.exists():
        raise FileNotFoundError(f"File not found: {BRIBES_ENRICHED_FILE}")
    if not FSN_DATA_FILE.exists():
        raise FileNotFoundError(f"File not found: {FSN_DATA_FILE}")
    
    bribes_df = pd.read_csv(BRIBES_ENRICHED_FILE)
    fsn_df = pd.read_csv(FSN_DATA_FILE)
    
    print(f"   ✓ Bribes_enriched: {len(bribes_df)} records")
    print(f"   ✓ FSN_data: {len(fsn_df)} records")
    
    # 1. Create lookups from FSN_data
    print("\n1. Creating lookup indexes from FSN_data...")
    
    # pool_to_gauge: {pool_42: [records]}
    pool_to_gauge = {}
    # gauge_to_pool: {gauge_address: record}
    gauge_to_pool = {}
    
    for _, row in fsn_df.iterrows():
        pool_id = row.get('poolId')
        gauge_id = row.get('id')
        chain = row.get('chain')
        status = row.get('status')
        
        if pd.notna(pool_id):
            p42 = extract_base_address(pool_id)
            if p42 not in pool_to_gauge: pool_to_gauge[p42] = []
            pool_to_gauge[p42].append({'id': gauge_id, 'chain': chain, 'status': status, 'poolId': pool_id})
            
        if pd.notna(gauge_id):
            g_addr = normalize_address(gauge_id)
            gauge_to_pool[g_addr] = {'poolId': pool_id, 'chain': chain, 'status': status, 'id': gauge_id}

    # 2. Fill missing data (with expansion support)
    print("\n2. Filling missing data and handling multiple gauges...")
    
    filled_count = 0
    
    # Flag to track if we expanded this row
    bribes_df['is_derived_gauge'] = False
    # Preserve original gauge if we later replace with a list of candidates
    if 'gauge_address_original' not in bribes_df.columns:
        bribes_df['gauge_address_original'] = bribes_df.get('gauge_address')
    # Add a temporary unique ID to track expansions
    bribes_df['temp_row_id'] = range(len(bribes_df))
    
    for idx, row in bribes_df.iterrows():
        pool_id = row.get('pool_id')
        gauge_addr = row.get('gauge_address')
        blockchain = row.get('blockchain')
        
        match = None
        matches = []
        p42 = None
        if pd.notna(pool_id) and pool_id != '':
            p42 = extract_base_address(pool_id)
        elif pd.notna(row.get('derived_pool_address')) and row.get('derived_pool_address') != '':
            p42 = extract_base_address(row.get('derived_pool_address'))
        
        # Scenario A: We have a gauge address. Verify/Fill details.
        if pd.notna(gauge_addr) and gauge_addr != '':
            g_norm = normalize_address(gauge_addr)
            if g_norm in gauge_to_pool:
                match = gauge_to_pool[g_norm]
                
                # Apply updates in place
                updated = False
                if pd.isna(pool_id) or pool_id == '':
                    bribes_df.at[idx, 'pool_id'] = match['poolId']
                    updated = True
                if pd.isna(blockchain) or blockchain == '':
                    bribes_df.at[idx, 'blockchain'] = match['chain']
                    updated = True
                if updated:
                    filled_count += 1
            # We still want to check if this pool has multiple gauges
            # so we can store the candidate list.
            if not p42 and match and pd.notna(match.get('poolId')):
                p42 = extract_base_address(match.get('poolId'))
            
        if p42 and p42 in pool_to_gauge:
            matches = pool_to_gauge[p42]

            if len(matches) == 1:
                # Single match: Update in place (only if missing)
                match = matches[0]
                if pd.isna(gauge_addr) or gauge_addr == '':
                    bribes_df.at[idx, 'gauge_address'] = match['id']
                if pd.isna(pool_id) or pool_id == '':
                    bribes_df.at[idx, 'pool_id'] = match['poolId']
                if pd.isna(blockchain) or blockchain == '':
                    bribes_df.at[idx, 'blockchain'] = match['chain']
                filled_count += 1

            else:
                # Multiple matches: store candidate gauges as a list-like JSON string
                gauge_candidates = [m['id'] for m in matches if pd.notna(m.get('id'))]
                status_candidates = [m.get('status', 'UNKNOWN') for m in matches]

                # Preserve original gauge in case it helps resolve later
                bribes_df.at[idx, 'gauge_address_original'] = gauge_addr
                bribes_df.at[idx, 'gauge_address'] = json.dumps(gauge_candidates)
                bribes_df.at[idx, 'gauge_status'] = json.dumps(status_candidates)
                bribes_df.at[idx, 'is_derived_gauge'] = True

                if pd.isna(pool_id) or pool_id == '':
                    bribes_df.at[idx, 'pool_id'] = matches[0].get('poolId')
                if pd.isna(blockchain) or blockchain == '':
                    bribes_df.at[idx, 'blockchain'] = matches[0].get('chain')
                filled_count += 1

    print(f"   ✓ Performed {filled_count} data fills/corrections (including expansions)")
    
    # Ensure pool_42 exists for downstream processing
    print("   + Updating/Creating pool_42 column...")
    bribes_df['pool_42'] = bribes_df['pool_id'].apply(extract_base_address)
    
    # 3. Save enriched file
    bribes_df.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✓ Saved to {OUTPUT_FILE}")
    
    return bribes_df


if __name__ == "__main__":
    try:
        enrich_bribes_with_fsn()
        print("\n✅ Enrichment completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
