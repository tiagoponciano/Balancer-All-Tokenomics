#!/usr/bin/env python3
"""
Script to debug why the merge is not working
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

print("=" * 70)
print("DEBUG: Merge Issue Investigation")
print("=" * 70)

# Load files
vebal_df = pd.read_csv(DATA_DIR / "veBAL.csv")
votes_bribes_df = pd.read_csv(DATA_DIR / "votes_bribes_merged.csv")

print("\n1. veBAL Sample:")
print(f"   Total rows: {len(vebal_df)}")
print(f"   Columns: {list(vebal_df.columns)}")
sample = vebal_df[vebal_df['gauge_address'].notna()].head(3)
print("\n   Sample rows:")
for idx, row in sample.iterrows():
    print(f"   - Date: {row['block_date']}")
    print(f"     Gauge: {row['gauge_address']}")
    print(f"     Blockchain: {row['blockchain']}")

print("\n2. votes_bribes_merged Sample:")
print(f"   Total rows: {len(votes_bribes_df)}")
print(f"   Columns: {list(votes_bribes_df.columns)}")
sample2 = votes_bribes_df[votes_bribes_df['gauge_address'].notna()].head(3)
print("\n   Sample rows:")
for idx, row in sample2.iterrows():
    print(f"   - Date: {row['day']}")
    print(f"     Gauge: {row['gauge_address']}")
    print(f"     Blockchain: {row['blockchain']}")

print("\n3. Checking overlapping gauges...")
vebal_gauges = set(vebal_df['gauge_address'].str.lower().str.strip().dropna())
votes_gauges = set(votes_bribes_df['gauge_address'].str.lower().str.strip().dropna())
overlap = vebal_gauges & votes_gauges
print(f"   veBAL unique gauges: {len(vebal_gauges)}")
print(f"   votes_bribes unique gauges: {len(votes_gauges)}")
print(f"   Overlapping gauges: {len(overlap)}")
if overlap:
    print(f"   Examples of overlapping gauges:")
    for g in list(overlap)[:5]:
        print(f"     - {g}")

print("\n4. Date format check...")
vebal_df['block_date'] = pd.to_datetime(vebal_df['block_date'], errors='coerce')
votes_bribes_df['day'] = pd.to_datetime(votes_bribes_df['day'], errors='coerce')

print(f"   veBAL date dtype: {vebal_df['block_date'].dtype}")
print(f"   votes_bribes date dtype: {votes_bribes_df['day'].dtype}")

print("\n5. Looking for exact matches...")
# Normalize
vebal_test = vebal_df[vebal_df['gauge_address'].notna()].copy()
vebal_test['gauge_lower'] = vebal_test['gauge_address'].str.lower().str.strip()
vebal_test['blockchain_lower'] = vebal_test['blockchain'].str.lower().str.strip()
vebal_test['date_only'] = vebal_test['block_date'].dt.date

votes_test = votes_bribes_df[votes_bribes_df['gauge_address'].notna()].copy()
votes_test['gauge_lower'] = votes_test['gauge_address'].str.lower().str.strip()
votes_test['blockchain_lower'] = votes_test['blockchain'].str.lower().str.strip()
votes_test['date_only'] = votes_test['day'].dt.date

# Try merge
merged_test = pd.merge(
    vebal_test[['gauge_lower', 'blockchain_lower', 'date_only']].drop_duplicates(),
    votes_test[['gauge_lower', 'blockchain_lower', 'date_only']].drop_duplicates(),
    on=['gauge_lower', 'blockchain_lower', 'date_only'],
    how='inner'
)

print(f"   Potential matches (by gauge + blockchain + date): {len(merged_test)}")

if len(merged_test) > 0:
    print("\n   ✅ Matches FOUND! The issue is in the merge logic.")
    print(f"   Sample matches:")
    print(merged_test.head(10))
else:
    print("\n   ❌ NO matches found even with normalization!")
    print("\n   Checking date overlap...")
    vebal_dates = set(vebal_test['date_only'])
    votes_dates = set(votes_test['date_only'])
    date_overlap = vebal_dates & votes_dates
    print(f"   veBAL unique dates: {len(vebal_dates)}")
    print(f"   votes_bribes unique dates: {len(votes_dates)}")
    print(f"   Overlapping dates: {len(date_overlap)}")
    
    if date_overlap:
        print(f"   Example overlapping dates: {list(date_overlap)[:5]}")

print("\n" + "=" * 70)
print("Investigation complete!")
print("=" * 70)
