#!/usr/bin/env python3
"""
Main script to fetch multiple Dune queries and generate CSVs
Also executes data collection from HiddenHand Finance
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent / "script"
sys.path.insert(0, str(SCRIPT_DIR))

from dune_fetcher import fetch_and_save

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("DUNE_API_KEY")

if not API_KEY:
    raise ValueError("DUNE_API_KEY not found in .env file")

QUERIES = {
    6623057: "veBAL.csv",
    6583834: "Bribes.csv",
    6608301: "Votes_Emissions.csv",
}


def run_dune_queries():
    """Processes all Dune queries"""
    print("=" * 60)
    print("Starting Dune data collection")
    print("=" * 60)
    print(f"Total queries: {len(QUERIES)}\n")
    
    results = []
    
    for query_id, output_file in QUERIES.items():
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


def run_create_final_dataset():
    """Creates final dataset combining veBAL.csv and votes_bribes_merged.csv"""
    print("\n" + "=" * 60)
    print("Starting final dataset creation")
    print("=" * 60 + "\n")
    

    from create_final_dataset import main as final_main
    final_main()


def main():
    """Main function that processes all data sources"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dune-only":
            run_dune_queries()
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
        elif sys.argv[1] == "--create-final":
            run_create_final_dataset()
            return
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python main.py [options]")
            print("\nOptions:")
            print("  (no options)          - Runs all sources (Dune + HiddenHand + Merge + Gauge + Classify + Final)")
            print("  --dune-only           - Runs only Dune queries")
            print("  --hiddenhand-only     - Runs only HiddenHand collection")
            print("  --merge-bribes        - Runs only Bribes data merge")
            print("  --add-gauge           - Adds gauge_address to veBAL.csv")
            print("  --merge-votes-bribes  - Merges Votes_Emissions and Bribes")
            print("  --classify-core-pools - Classifies pools as core or non-core")
            print("  --create-final        - Creates final dataset (Balancer-All-Tokenomics.csv)")
            print("  --help, -h            - Shows this message")
            return
    
    run_dune_queries()
    run_hiddenhand()
    # run_merge_bribes()  # DISABLED: Keeping Dune and HiddenHand data separated for now
    run_add_gauge_address()
    run_merge_votes_bribes()
    run_classify_core_pools()
    run_create_final_dataset()
    
    print("\n" + "=" * 60)
    print("All data collection and processing completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
