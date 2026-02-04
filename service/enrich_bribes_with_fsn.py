#!/usr/bin/env python3
"""
Script to enrich Bribes_enriched.csv with missing blockchain and gauge_address from FSN_data.csv

Matching logic:
- Compare pool_id/derived_pool_address from Bribes_enriched with poolId from FSN_data
- Use first 42 characters for matching (Ethereum address standard)
- Fill missing blockchain (chain) and gauge_address (id) where there's a match
"""
import pandas as pd
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

BRIBES_ENRICHED_FILE = DATA_DIR / "Bribes_enriched.csv"
FSN_DATA_FILE = DATA_DIR / "FSN_data.csv"
OUTPUT_FILE = DATA_DIR / "Bribes_enriched.csv"  # Overwrite the enriched file


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
    Enriches Bribes_enriched.csv with missing blockchain and gauge_address from FSN_data.csv
    """
    print("=" * 70)
    print("Enriching Bribes with FSN Data")
    print("=" * 70)
    
    # 1. Load files
    print("\n1. Loading CSV files...")
    
    if not BRIBES_ENRICHED_FILE.exists():
        raise FileNotFoundError(f"File not found: {BRIBES_ENRICHED_FILE}")
    
    if not FSN_DATA_FILE.exists():
        raise FileNotFoundError(f"File not found: {FSN_DATA_FILE}")
    
    bribes_df = pd.read_csv(BRIBES_ENRICHED_FILE)
    fsn_df = pd.read_csv(FSN_DATA_FILE)
    
    print(f"   ✓ Bribes_enriched: {len(bribes_df)} records")
    print(f"   ✓ FSN_data: {len(fsn_df)} records")
    
    # 2. Analyze missing data
    print("\n2. Analyzing missing data in Bribes_enriched...")
    
    missing_blockchain = bribes_df['blockchain'].isna().sum() + (bribes_df['blockchain'] == '').sum()
    missing_gauge = bribes_df['gauge_address'].isna().sum() + (bribes_df['gauge_address'] == '').sum()
    
    print(f"   - Missing blockchain: {missing_blockchain} records")
    print(f"   - Missing gauge_address: {missing_gauge} records")
    
    if missing_blockchain == 0 and missing_gauge == 0:
        print("   ✓ No missing data detected!")
        return bribes_df
    
    # 3. Create lookup index from FSN_data
    print("\n3. Creating lookup index from FSN_data...")
    print("   - Extracting first 42 characters from poolId...")
    
    # Create lookup dictionary: {base_address_42: [fsn_records]}
    fsn_lookup = {}
    
    for _, row in fsn_df.iterrows():
        pool_id = row.get('poolId')
        if pd.notna(pool_id):
            base_addr = extract_base_address(pool_id)
            if base_addr:
                if base_addr not in fsn_lookup:
                    fsn_lookup[base_addr] = []
                
                fsn_lookup[base_addr].append({
                    'gauge_address': row.get('id'),
                    'blockchain': row.get('chain'),
                    'status': row.get('status'),
                    'poolId': pool_id
                })
    
    print(f"   ✓ Created lookup with {len(fsn_lookup)} unique pool addresses (42 chars)")
    
    # 4. Fill missing data AND correct wrong gauge addresses
    print("\n4. Filling missing blockchain and correcting gauge_address...")
    
    filled_blockchain = 0
    filled_gauge = 0
    corrected_gauge = 0
    matched_pools = set()
    
    for idx, row in bribes_df.iterrows():
        # Get pool identifiers from bribes
        pool_id = row.get('pool_id')
        derived_address = row.get('derived_pool_address')
        current_gauge = row.get('gauge_address')
        
        # Try to get base address (first 42 chars) from multiple sources
        base_addr = None
        
        # First try: pool_id
        if pd.notna(pool_id) and pool_id != '':
            base_addr = extract_base_address(pool_id)
        
        # Second try: derived_pool_address
        if not base_addr and pd.notna(derived_address) and derived_address != '':
            base_addr = extract_base_address(derived_address)
        
        # Third try: gauge_address itself (might be a pool address)
        if not base_addr and pd.notna(current_gauge) and current_gauge != '':
            base_addr = extract_base_address(current_gauge)
        
        # If we have a base address and it exists in FSN data
        if base_addr and base_addr in fsn_lookup:
            fsn_matches = fsn_lookup[base_addr]
            matched_pools.add(base_addr)
            
            # Prefer active gauges
            fsn_record = None
            for match in fsn_matches:
                if match.get('status', '').upper() == 'ACTIVE':
                    fsn_record = match
                    break
            
            # If no active, take first one
            if not fsn_record:
                fsn_record = fsn_matches[0]
            
            # Fill missing blockchain
            current_blockchain = row.get('blockchain')
            if pd.isna(current_blockchain) or current_blockchain == '':
                if pd.notna(fsn_record.get('blockchain')):
                    bribes_df.at[idx, 'blockchain'] = fsn_record['blockchain']
                    filled_blockchain += 1
            
            # ALWAYS update gauge_address with the correct one from FSN
            # (fixes cases where gauge_address is actually a pool address)
            if pd.notna(fsn_record.get('gauge_address')):
                old_gauge = normalize_address(current_gauge)
                new_gauge = normalize_address(fsn_record['gauge_address'])
                
                if not current_gauge or pd.isna(current_gauge) or current_gauge == '':
                    # Missing gauge - fill it
                    bribes_df.at[idx, 'gauge_address'] = fsn_record['gauge_address']
                    filled_gauge += 1
                elif old_gauge != new_gauge:
                    # Wrong gauge - correct it
                    bribes_df.at[idx, 'gauge_address'] = fsn_record['gauge_address']
                    corrected_gauge += 1
    
    print(f"   ✓ Filled {filled_blockchain} missing blockchain values")
    print(f"   ✓ Filled {filled_gauge} missing gauge_address values")
    print(f"   ✓ Corrected {corrected_gauge} wrong gauge_address values")
    print(f"   ✓ Matched {len(matched_pools)} unique pools with FSN data")
    
    # 5. Final statistics
    print("\n5. Final statistics:")
    
    remaining_missing_blockchain = bribes_df['blockchain'].isna().sum() + (bribes_df['blockchain'] == '').sum()
    remaining_missing_gauge = bribes_df['gauge_address'].isna().sum() + (bribes_df['gauge_address'] == '').sum()
    
    print(f"   - Total records: {len(bribes_df)}")
    print(f"   - Records with blockchain: {len(bribes_df) - remaining_missing_blockchain}")
    print(f"   - Records with gauge_address: {len(bribes_df) - remaining_missing_gauge}")
    print(f"   - Still missing blockchain: {remaining_missing_blockchain}")
    print(f"   - Still missing gauge_address: {remaining_missing_gauge}")
    
    if remaining_missing_blockchain > 0 or remaining_missing_gauge > 0:
        print("\n   ⚠️  Some records still missing data (no match found in FSN_data)")
    
    # 6. Save enriched file
    print(f"\n6. Saving enriched file...")
    print(f"   - {OUTPUT_FILE}")
    
    bribes_df.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✓ File saved successfully!")
    
    print("\n" + "=" * 70)
    print("Enrichment completed!")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  - Blockchain filled: {filled_blockchain}")
    print(f"  - Gauge addresses filled: {filled_gauge}")
    print(f"  - Gauge addresses corrected: {corrected_gauge}")
    print(f"  - Pools matched with FSN: {len(matched_pools)}")
    print(f"  - Output file: {OUTPUT_FILE}")
    
    return bribes_df


def main():
    """
    Main function to execute the enrichment process.
    
    Returns:
        DataFrame with enriched bribe data
        
    Raises:
        FileNotFoundError: If input files don't exist
    """
    try:
        result_df = enrich_bribes_with_fsn()
        print("\n" + "=" * 70)
        print("✅ Process completed successfully!")
        print("=" * 70)
        return result_df
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
