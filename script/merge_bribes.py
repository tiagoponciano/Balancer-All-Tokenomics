import pandas as pd
import os
from pathlib import Path

DATA_DIR = "../data"
BALANCER_CSV = os.path.join(DATA_DIR, "Bribes.csv")
HIDDENHAND_CSV = os.path.join(DATA_DIR, "hiddenhand_bribes.csv")
GAUGES_CSV = os.path.join(DATA_DIR, "FSN_data.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "Bribes_enriched.csv")

def normalize_proposal_hash(hash_str):
    if pd.isna(hash_str) or hash_str == '':
        return None
    return str(hash_str).strip().lower()


def merge_bribes_data():
    print("=" * 70)
    print("Data Merge: Balancer_Bribes_Gauges + HiddenHand")
    print("=" * 70)
    
    print("\n1. Loading CSVs...")
    print(f"   - {BALANCER_CSV}")
    balancer_df = pd.read_csv(BALANCER_CSV)
    print(f"   ✓ Loaded: {len(balancer_df)} records")
    
    print(f"   - {HIDDENHAND_CSV}")
    hiddenhand_df = pd.read_csv(HIDDENHAND_CSV)
    print(f"   ✓ Loaded: {len(hiddenhand_df)} records")
    
    print("\n2. Normalizing proposal_hash...")
    balancer_df['proposal_hash_normalized'] = balancer_df['proposal_hash'].apply(normalize_proposal_hash)
    hiddenhand_df['proposal_hash_normalized'] = hiddenhand_df['proposal_hash'].apply(normalize_proposal_hash)
    
    hiddenhand_valid = hiddenhand_df[hiddenhand_df['proposal_hash_normalized'].notna()].copy()
    print(f"   ✓ HiddenHand with valid proposal_hash: {len(hiddenhand_valid)} records")
    
    print("\n3. Creating lookup index...")
    hiddenhand_dict = {}
    for _, row in hiddenhand_valid.iterrows():
        hash_key = row['proposal_hash_normalized']
        if hash_key not in hiddenhand_dict:
            hiddenhand_dict[hash_key] = []
        hiddenhand_dict[hash_key].append(row)
    
    print(f"   ✓ {len(hiddenhand_dict)} unique proposal_hashes in HiddenHand")
    
    print("\n4. Analyzing missing fields in Balancer_Bribes_Gauges...")
    balancer_cols = set(balancer_df.columns)
    hiddenhand_cols = set(hiddenhand_df.columns)
    
    fillable_fields = {
        'pool_id': 'pool_id',
        'pool_name': 'pool_name',
        'derived_pool_address': 'derived_pool_address',
        'week_timestamp': 'week_timestamp',
        'week_date': 'week_date'
    }
    
    missing_stats = {}
    for hidden_col, balancer_col in fillable_fields.items():
        if hidden_col in hiddenhand_cols:
            if balancer_col not in balancer_cols:
                missing_stats[balancer_col] = 'field_does_not_exist'
            else:
                missing_count = balancer_df[balancer_col].isna().sum() + (balancer_df[balancer_col] == '').sum()
                if missing_count > 0:
                    missing_stats[balancer_col] = missing_count
    
    if missing_stats:
        print("   Fields with missing data:")
        for field, count in missing_stats.items():
            if count == 'field_does_not_exist':
                print(f"     - {field}: field does not exist (will be added)")
            else:
                print(f"     - {field}: {count} missing values")
    else:
        print("   ✓ No missing fields detected")
    
    print("\n5. Preparing DataFrame for enrichment...")
    new_columns = []
    for hidden_col, balancer_col in fillable_fields.items():
        if balancer_col not in balancer_df.columns:
            balancer_df[balancer_col] = None
            new_columns.append(balancer_col)
            print(f"   + Added column: {balancer_col}")
    
    if 'pool_name' not in balancer_df.columns:
        balancer_df['pool_name'] = None
        new_columns.append('pool_name')
        print(f"   + Added column: pool_name")
    
    if 'derived_pool_address' not in balancer_df.columns:
        balancer_df['derived_pool_address'] = None
        new_columns.append('derived_pool_address')
    
    if 'week_timestamp' not in balancer_df.columns:
        balancer_df['week_timestamp'] = None
        new_columns.append('week_timestamp')
    if 'week_date' not in balancer_df.columns:
        balancer_df['week_date'] = None
        new_columns.append('week_date')
    
    print("\n6. Filling missing data...")
    filled_count = 0
    matched_hashes = set()
    
    for idx, row in balancer_df.iterrows():
        hash_key = row['proposal_hash_normalized']
        
        if hash_key and hash_key in hiddenhand_dict:
            hiddenhand_row = hiddenhand_dict[hash_key][0]
            matched_hashes.add(hash_key)
            
            updates = 0
            
            if pd.isna(row['pool_id']) or row['pool_id'] == '':
                if pd.notna(hiddenhand_row.get('pool_id')):
                    balancer_df.at[idx, 'pool_id'] = hiddenhand_row['pool_id']
                    updates += 1
            
            if pd.notna(hiddenhand_row.get('pool_name')):
                hiddenhand_pool_name = str(hiddenhand_row['pool_name']).strip()
                balancer_df.at[idx, 'pool_title'] = hiddenhand_pool_name
                updates += 1
            
            if 'pool_name' in balancer_df.columns:
                if pd.notna(hiddenhand_row.get('pool_name')):
                    balancer_df.at[idx, 'pool_name'] = hiddenhand_row['pool_name']
                    updates += 1
            
            if pd.isna(row['derived_pool_address']) or row['derived_pool_address'] == '':
                if pd.notna(hiddenhand_row.get('derived_pool_address')):
                    balancer_df.at[idx, 'derived_pool_address'] = hiddenhand_row['derived_pool_address']
                    updates += 1
            
            if pd.isna(row['week_timestamp']):
                if pd.notna(hiddenhand_row.get('week_timestamp')):
                    balancer_df.at[idx, 'week_timestamp'] = hiddenhand_row['week_timestamp']
                    updates += 1
            
            if pd.isna(row['week_date']) or row['week_date'] == '':
                if pd.notna(hiddenhand_row.get('week_date')):
                    balancer_df.at[idx, 'week_date'] = hiddenhand_row['week_date']
                    updates += 1
            
            if updates > 0:
                filled_count += 1
    
    print(f"   ✓ {filled_count} records filled")
    print(f"   ✓ {len(matched_hashes)} matching proposal_hashes found")
    
    balancer_df = balancer_df.drop(columns=['proposal_hash_normalized'], errors='ignore')
    
    print("\n7. Final statistics:")
    print(f"   - Total records: {len(balancer_df)}")
    print(f"   - Records with proposal_hash: {balancer_df['proposal_hash'].notna().sum()}")
    
    if 'pool_id' in balancer_df.columns:
        print(f"   - Records with pool_id: {balancer_df['pool_id'].notna().sum()}")
    if 'pool_title' in balancer_df.columns:
        print(f"   - Records with pool_title: {balancer_df['pool_title'].notna().sum()}")
    if 'pool_name' in balancer_df.columns:
        print(f"   - Records with pool_name: {balancer_df['pool_name'].notna().sum()}")
    if 'derived_pool_address' in balancer_df.columns:
        print(f"   - Records with derived_pool_address: {balancer_df['derived_pool_address'].notna().sum()}")
    
    print(f"\n8. Saving enriched CSV...")
    print(f"   - {OUTPUT_CSV}")
    balancer_df.to_csv(OUTPUT_CSV, index=False)
    print(f"   ✓ File saved successfully!")
    
    print("\n" + "=" * 70)
    print("Merge completed!")
    print("=" * 70)
    print("\n" + "=" * 70)
    print("Merge with Gauges: Filling gauge_address")
    print("=" * 70)
    
    print(f"\n8. Loading {GAUGES_CSV}...")
    gauges_df = pd.read_csv(GAUGES_CSV)
    print(f"   ✓ Loaded: {len(gauges_df)} records")
    
    def normalize_address(addr):
        if pd.isna(addr) or addr == '':
            return None
        return str(addr).strip().lower()
    
    print("\n9. Creating lookup index by pool_address + blockchain...")
    gauges_dict = {}
    
    for _, row in gauges_df.iterrows():
        pool_addr = normalize_address(row.get('pool_address'))
        blockchain = str(row.get('blockchain', '')).strip().lower() if pd.notna(row.get('blockchain')) else None
        gauge_addr = row.get('address')
        
        if pool_addr and blockchain and pd.notna(gauge_addr):
            key = (pool_addr, blockchain)
            if key not in gauges_dict:
                gauges_dict[key] = []
            gauges_dict[key].append({
                'gauge_address': gauge_addr,
                'child_gauge_address': row.get('child_gauge_address'),
                'name': row.get('name'),
                'status': row.get('status')
            })
    
    print(f"   ✓ {len(gauges_dict)} unique keys (pool_address + blockchain)")
    
    print("\n10. Filling missing gauge_address...")
    gauge_filled_count = 0
    
    def extract_base_address(address_str):
        if not address_str:
            return None
        addr = str(address_str).strip().lower()
        if addr.startswith('0x') and len(addr) >= 42:
            return addr[:42]
        return addr
    
    for idx, row in balancer_df.iterrows():
        pool_id_raw = row.get('pool_id')
        pool_id = normalize_address(pool_id_raw)
        pool_id_base = extract_base_address(pool_id_raw) if pool_id else None
        
        if not pool_id:
            derived_addr = row.get('derived_pool_address')
            pool_id = normalize_address(derived_addr)
            pool_id_base = extract_base_address(derived_addr) if derived_addr else None
        
        blockchain = str(row.get('blockchain', '')).strip().lower() if pd.notna(row.get('blockchain')) else None
        
        if blockchain:
            key = None
            if pool_id:
                key = (pool_id, blockchain)
            
            if (not key or key not in gauges_dict) and pool_id_base:
                key = (pool_id_base, blockchain)
            
            if key and key in gauges_dict:
                gauge_info = None
                for g in gauges_dict[key]:
                    if g.get('status') == 'active':
                        gauge_info = g
                        break
                
                if not gauge_info:
                    gauge_info = gauges_dict[key][0]
                
                current_gauge = str(row.get('gauge_address', '')).strip().lower() if pd.notna(row.get('gauge_address')) else ''
                new_gauge = str(gauge_info['gauge_address']).strip().lower()
                
                if current_gauge == '' or current_gauge != new_gauge:
                    balancer_df.at[idx, 'gauge_address'] = gauge_info['gauge_address']
                    gauge_filled_count += 1
    
    print(f"   ✓ {gauge_filled_count} gauge_address filled")
    
    print("\n11. Updated final statistics:")
    print(f"   - Total records: {len(balancer_df)}")
    print(f"   - Records with proposal_hash: {balancer_df['proposal_hash'].notna().sum()}")
    
    if 'pool_id' in balancer_df.columns:
        print(f"   - Records with pool_id: {balancer_df['pool_id'].notna().sum()}")
    if 'pool_title' in balancer_df.columns:
        print(f"   - Records with pool_title: {balancer_df['pool_title'].notna().sum()}")
    if 'pool_name' in balancer_df.columns:
        print(f"   - Records with pool_name: {balancer_df['pool_name'].notna().sum()}")
    if 'gauge_address' in balancer_df.columns:
        print(f"   - Records with gauge_address: {balancer_df['gauge_address'].notna().sum()}")
    if 'derived_pool_address' in balancer_df.columns:
        print(f"   - Records with derived_pool_address: {balancer_df['derived_pool_address'].notna().sum()}")
    
    print(f"\n12. Saving updated enriched CSV...")
    print(f"   - {OUTPUT_CSV}")
    balancer_df.to_csv(OUTPUT_CSV, index=False)
    print(f"   ✓ File saved successfully!")
    
    print("\n" + "=" * 70)
    print("Merge completed!")
    print("=" * 70)
    print(f"\nGenerated file: {OUTPUT_CSV}")
    print(f"Total records: {len(balancer_df)}")
    print(f"Records filled (HiddenHand): {filled_count}")
    print(f"Matching proposal hashes: {len(matched_hashes)}")
    print(f"Gauge addresses filled: {gauge_filled_count}")


if __name__ == "__main__":
    merge_bribes_data()
