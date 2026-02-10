#!/usr/bin/env python3
"""
Main script to fetch multiple Dune queries and generate CSVs
Also executes data collection from HiddenHand Finance
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

SCRIPT_DIR = Path(__file__).parent / "service"
sys.path.insert(0, str(SCRIPT_DIR))

from dune_fetcher import fetch_and_save
from dune_fetcher_chunked import fetch_and_save_chunked

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("DUNE_API_KEY")
if not API_KEY:
    raise ValueError("DUNE_API_KEY not found in .env file")

# Default date range - can be overridden via environment variables or command line
DEFAULT_START_DATE = os.getenv("START_DATE", "2024-01-01")
DEFAULT_END_DATE = os.getenv("END_DATE", datetime.now().strftime("%Y-%m-%d"))

QUERIES = {
    6644710: "veBAL.csv",
    6583834: "Bribes.csv",
    6608301: "Votes_Emissions.csv",
}

# Query 6644710 is the large one that needs chunking
CHUNKED_QUERY_ID = 6644710
CHUNK_DAYS = 45  # Fetch 45 days at a time (smaller chunks reduce timeouts)

def run_dune_queries(start_date: str = None, end_date: str = None, merge_vebal_with_existing: bool = False):
    """
    Processes all Dune queries.
    When merge_vebal_with_existing=True (incremental run), new veBAL chunk is merged with existing veBAL.csv.
    """
    # Use provided dates or defaults
    start_date = start_date or DEFAULT_START_DATE
    end_date = end_date or DEFAULT_END_DATE
    
    print("=" * 60)
    print("Starting Dune data collection")
    print("=" * 60)
    print(f"Total queries: {len(QUERIES)}")
    print(f"Date range for query {CHUNKED_QUERY_ID}: {start_date} to {end_date}\n")
    
    results = []
    
    for query_id, output_file in QUERIES.items():
        # Use chunked fetching for the large query
        if query_id == CHUNKED_QUERY_ID:
            success, rows, path = fetch_and_save_chunked(
                api_key=API_KEY,
                query_id=query_id,
                start_date=start_date,
                end_date=end_date,
                output_filename=output_file,
                project_root=PROJECT_ROOT,
                chunk_days=CHUNK_DAYS,
                merge_with_existing=merge_vebal_with_existing,
            )
        else:
            # Use regular fetching for other queries
            success, rows, path = fetch_and_save(
                api_key=API_KEY,
                query_id=query_id,
                output_filename=output_file,
                project_root=PROJECT_ROOT
            )
        
        results.append({
            'query_id': query_id,
            'output_file': output_file,
            'success': success,
            'rows': rows,
            'path': path
        })
    
    # Final summary
    print("=" * 60)
    print("Execution Summary - Dune")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['success'])
    total_rows = sum(r['rows'] for r in results)
    
    for result in results:
        status = "✓" if result['success'] else "✗"
        print(f"{status} Query {result['query_id']}: {result['output_file']} ({result['rows']} rows)")
    
    print(f"\nTotal: {successful}/{len(results)} queries processed successfully")
    print(f"Total rows: {total_rows}")
    print("=" * 60)
    
    return results

def run_hiddenhand():
    """Executes HiddenHand Finance data collection"""
    print("\n" + "=" * 60)
    print("Starting HiddenHand Finance data collection")
    print("=" * 60 + "\n")
    
    from fetch_hiddenhand import main as hiddenhand_main
    hiddenhand_main()

def run_merge_bribes():
    """Executes merge of bribe data from Dune and HiddenHand"""
    print("\n" + "=" * 60)
    print("Starting Bribes data merge")
    print("=" * 60 + "\n")
    
    from merge_bribes import main as merge_main
    merge_main()

def run_add_gauge_address():
    """Adds gauge_address to veBAL.csv based on FSN_data.csv"""
    print("\n" + "=" * 60)
    print("Starting gauge_address addition to veBAL")
    print("=" * 60 + "\n")
    
    from add_gauge_address import main as gauge_main
    gauge_main()

def run_merge_votes_bribes():
    """Merges Votes_Emissions.csv and Bribes.csv"""
    print("\n" + "=" * 60)
    print("Starting Votes_Emissions and Bribes merge")
    print("=" * 60 + "\n")
    
    from merge_votes_bribes import main as merge_votes_main
    merge_votes_main()

def run_classify_core_pools():
    """Classifies pools as core or non-core based on historical data"""
    print("\n" + "=" * 60)
    print("Starting Core Pools classification")
    print("=" * 60 + "\n")
    
    from classify_core_pools import main as classify_main
    classify_main()

def run_enrich_bribes_with_fsn():
    """Enriches Bribes_enriched.csv with missing blockchain and gauge_address from FSN_data.csv"""
    print("\n" + "=" * 60)
    print("Starting Bribes enrichment with FSN data")
    print("=" * 60 + "\n")
    
    from enrich_bribes_with_fsn import main as enrich_main
    enrich_main()

def run_create_final_dataset():
    """Creates final dataset combining veBAL.csv and votes_bribes_merged.csv"""
    print("\n" + "=" * 60)
    print("Starting final dataset creation")
    print("=" * 60 + "\n")
    
    from create_final_dataset import main as final_main
    final_main()


def run_upload_to_neon():
    """Upload final CSVs to NEON (or any Postgres) for the Streamlit app."""
    print("\n" + "=" * 60)
    print("Uploading tokenomics data to NEON")
    print("=" * 60 + "\n")
    try:
        from upload_to_neon import main as neon_main
        neon_main()
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise

def parse_args():
    """Parse command line arguments for dates."""
    start_date = None
    end_date = None

    for i, arg in enumerate(sys.argv):
        if arg == "--start-date" and i + 1 < len(sys.argv):
            start_date = sys.argv[i + 1]
        elif arg == "--end-date" and i + 1 < len(sys.argv):
            end_date = sys.argv[i + 1]

    return start_date, end_date


def get_date_range_for_run(start_date=None, end_date=None):
    """
    Resolve (start_date, end_date, is_incremental) for Dune fetch.
    If both dates are None, use incremental range: from the day after the last
    existing record (in NEON or local CSV) to today. is_incremental=True means
    we should merge new veBAL with existing veBAL.csv.
    """
    if start_date is not None and end_date is not None:
        return start_date, end_date, False
    if start_date is not None:
        return start_date, end_date or datetime.now().strftime("%Y-%m-%d"), False
    if end_date is not None:
        return start_date or DEFAULT_START_DATE, end_date, False
    # No dates given: use incremental (last date in data + 1 → today)
    use_incremental = os.getenv("INCREMENTAL", "1").strip().lower() in ("1", "true", "yes")
    if use_incremental:
        sys.path.insert(0, str(SCRIPT_DIR))
        from get_last_date import get_incremental_date_range
        start_date, end_date, last = get_incremental_date_range(default_start=DEFAULT_START_DATE)
        if last:
            print(f"📅 Incremental run: last existing date = {last} → fetching {start_date} to {end_date}")
        return start_date, end_date, True
    return DEFAULT_START_DATE, end_date or datetime.now().strftime("%Y-%m-%d"), False

def main():
    """Main function that processes all data sources"""
    start_date, end_date = parse_args()
    # Resolve date range (incremental: from day after last record to today when no dates given)
    start_date, end_date, is_incremental = get_date_range_for_run(start_date, end_date)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--dune-only":
            run_dune_queries(start_date, end_date, merge_vebal_with_existing=is_incremental)
            return
        elif sys.argv[1] == "--hiddenhand-only":
            run_hiddenhand()
            return
        elif sys.argv[1] == "--merge-bribes":
            run_merge_bribes()
            return
        elif sys.argv[1] == "--add-gauge":
            run_add_gauge_address()
            return
        elif sys.argv[1] == "--merge-votes-bribes":
            run_merge_votes_bribes()
            return
        elif sys.argv[1] == "--classify-core-pools":
            run_classify_core_pools()
            return
        elif sys.argv[1] == "--enrich-bribes-fsn":
            run_enrich_bribes_with_fsn()
            return
        elif sys.argv[1] == "--create-final":
            run_create_final_dataset()
            return
        elif sys.argv[1] == "--upload-to-neon":
            run_upload_to_neon()
            return
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python main.py [options]")
            print("\nOptions:")
            print("  (no options)              - Runs all sources (Dune + HiddenHand + Merge Bribes + FSN + Gauge + Classify + Final)")
            print("  --dune-only               - Runs only Dune queries (veBAL in 45-day chunks)")
            print("  --hiddenhand-only         - Runs only HiddenHand collection")
            print("  --merge-bribes            - Runs only Bribes data merge (Dune + HiddenHand → Bribes_enriched)")
            print("  --add-gauge               - Adds gauge_address to veBAL.csv")
            print("  --merge-votes-bribes      - Merges Votes_Emissions and Bribes")
            print("  --classify-core-pools     - Classifies pools as core or non-core")
            print("  --enrich-bribes-fsn       - Enriches Bribes with FSN data (blockchain + gauge)")
            print("  --create-final            - Creates final dataset (Balancer-All-Tokenomics.csv)")
            print("  --upload-to-neon          - Upload final CSV to NEON/Postgres (set DATABASE_URL in .env)")
            print("  --help, -h                - Shows this message")
            print("\nDate Parameters (for chunked query 6644710):")
            print("  --start-date YYYY-MM-DD   - Set start date (default: incremental = day after last data)")
            print("  --end-date YYYY-MM-DD     - Set end date (default: today)")
            print("  INCREMENTAL=0             - Disable incremental; use START_DATE/2024-01-01 to today")
            print("\nExamples:")
            print("  python main.py --dune-only                    # incremental: from last date+1 to today")
            print("  python main.py --dune-only --start-date 2024-01-01 --end-date 2026-02-08")
            return
    
    # Run all steps (merge new veBAL with existing when incremental)
    run_dune_queries(start_date, end_date, merge_vebal_with_existing=is_incremental)
    run_hiddenhand()
    run_merge_bribes()  # Merge Dune Bribes + HiddenHand → Bribes_enriched
    run_enrich_bribes_with_fsn()  # Enrich Bribes_enriched with FSN data
    run_add_gauge_address()
    run_merge_votes_bribes()
    run_classify_core_pools()
    run_create_final_dataset()
    # Optional: upload to NEON so the app can load from DB (no large CSV on Supabase)
    if os.getenv("DATABASE_URL"):
        run_upload_to_neon()
    else:
        print("\n💡 Set DATABASE_URL in .env to auto-upload to NEON after each run.")
    
    print("\n" + "=" * 60)
    print("All data collection and processing completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()