"""
Script to collect bribe proposal data from HiddenHand Finance API for Balancer
"""
import os
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_BASE_URL = "https://api.hiddenhand.finance/proposal/balancer"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "hiddenhand_bribes.csv"

START_TIMESTAMP = 1649894400
REQUEST_DELAY = 1


def calculate_weekly_timestamps(start_timestamp: int, end_date: Optional[datetime] = None) -> List[int]:
    """
    Calculates weekly timestamps from the start date until today.
    
    Generates a list of timestamps, one for each week, starting from the
    specified start_timestamp and continuing until the end_date (default: today).
    Each timestamp represents the beginning of a week.
    
    Args:
        start_timestamp: Initial timestamp (Unix timestamp)
        end_date: End date (default: current date/time)
        
    Returns:
        List of weekly timestamps (Unix timestamps)
    """
    if end_date is None:
        end_date = datetime.now()
    
    timestamps = []
    current_timestamp = start_timestamp
    seconds_per_week = 7 * 24 * 60 * 60
    
    end_timestamp = int(end_date.timestamp())
    
    while current_timestamp <= end_timestamp:
        timestamps.append(current_timestamp)
        current_timestamp += seconds_per_week
    
    return timestamps


def fetch_proposal_data(timestamp: int, retry_count: int = 2) -> Optional[Dict]:
    """
    Fetches proposal data for a specific week.
    
    Makes HTTP GET request to HiddenHand Finance API for the specified timestamp.
    Implements retry logic for handling errors (500 status, timeouts, etc.).
    
    Args:
        timestamp: Week timestamp to fetch data for
        retry_count: Number of retry attempts in case of error
        
    Returns:
        JSON data from the API response or None if request fails
    """
    url = f"{API_BASE_URL}/{timestamp}"
    
    for attempt in range(retry_count + 1):
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 500:
                if attempt < retry_count:
                    wait_time = (attempt + 1) * 2
                    print(f" (attempt {attempt + 1}/{retry_count + 1}, waiting {wait_time}s)...", end="", flush=True)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Error 500 after {retry_count + 1} attempts")
                    return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < retry_count:
                print(f" (timeout, retrying)...", end="", flush=True)
                time.sleep(2)
                continue
            print(f"Timeout after {retry_count + 1} attempts")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < retry_count and "500" in str(e):
                wait_time = (attempt + 1) * 2
                print(f" (error, retrying in {wait_time}s)...", end="", flush=True)
                time.sleep(wait_time)
                continue
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    return None


def parse_proposal_data(json_data: Dict, timestamp: int) -> List[Dict]:
    """
    Extracts relevant information from the API JSON response.
    
    Parses the JSON response from HiddenHand Finance API and extracts
    proposal information including proposal hash, pool name, pool ID,
    and derived pool address.
    
    Args:
        json_data: JSON data from API response
        timestamp: Week timestamp
        
    Returns:
        List of dictionaries with extracted data, each containing:
        - week_timestamp: Timestamp of the week
        - week_date: Formatted date string (YYYY-MM-DD)
        - proposal_hash: Unique proposal hash
        - pool_name: Name of the pool
        - pool_id: Pool identifier
        - derived_pool_address: Pool address extracted from pool_id (first 42 chars)
    """
    results = []
    
    if not json_data:
        return results
    
    proposals = []
    
    if 'error' in json_data:
        error_value = json_data.get('error')
        if error_value is True:
            pass
    
    if 'data' in json_data:
        data_content = json_data.get('data')
        if isinstance(data_content, list):
            proposals = data_content
        elif data_content is None:
            proposals = []
        elif isinstance(data_content, dict):
            proposals = data_content.get('proposals', data_content.get('items', []))
    elif isinstance(json_data, list):
        proposals = json_data
    else:
        proposals = json_data.get('proposals', json_data.get('results', []))
    
    if not proposals:
        return results
    
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
            
        proposal_hash = proposal.get('proposalHash', '') or proposal.get('proposal_hash', '')
        pool_name = proposal.get('title', '') or proposal.get('pool_name', '') or proposal.get('name', '')
        pool_id = proposal.get('poolId', '') or proposal.get('pool_id', '')
        
        derived_pool_address = None
        if pool_id:
            if len(pool_id) >= 42:
                derived_pool_address = pool_id[:42].lower()
            elif pool_id.startswith('0x'):
                derived_pool_address = pool_id.lower()
        
        week_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        results.append({
            'week_timestamp': timestamp,
            'week_date': week_date,
            'proposal_hash': proposal_hash,
            'pool_name': pool_name,
            'pool_id': pool_id,
            'derived_pool_address': derived_pool_address,
        })
    
    return results


def main():
    """
    Main function to execute the HiddenHand Finance data collection process.
    
    Collects bribe proposal data from HiddenHand Finance API for Balancer,
    processing weekly timestamps from April 13, 2022 until the current date.
    Saves collected data to hiddenhand_bribes.csv with deduplication and
    sorting by timestamp (most recent first).
    
    The function:
    1. Calculates all weekly timestamps since the start date
    2. Fetches proposal data for each week with retry logic
    3. Parses and extracts relevant information
    4. Saves partial progress every 10 weeks
    5. Removes duplicates and saves final CSV
    
    Returns:
        None
        
    Raises:
        FileNotFoundError: If data directory cannot be created
        requests.exceptions.RequestException: If API requests fail consistently
    """
    print("=" * 60)
    print("HiddenHand Finance Data Collector")
    print("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    start_date_str = datetime.fromtimestamp(START_TIMESTAMP).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\nCalculating weekly timestamps since {start_date_str} (timestamp: {START_TIMESTAMP})...")
    timestamps = calculate_weekly_timestamps(START_TIMESTAMP)
    print(f"Total weeks to process: {len(timestamps)}")
    
    all_data = []
    successful = 0
    failed = 0
    empty_responses = 0
    
    print("\nStarting data collection...")
    print("-" * 60)
    
    for i, timestamp in enumerate(timestamps, 1):
        week_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        print(f"[{i}/{len(timestamps)}] Processing week of {week_date} (timestamp: {timestamp})...", end=" ", flush=True)
        
        json_data = fetch_proposal_data(timestamp)
        
        if json_data:
            if i == 1 or (i <= 5):
                response_keys = list(json_data.keys()) if isinstance(json_data, dict) else 'list'
                print(f"\n  [DEBUG] Structure: {response_keys}", end=" ")
                if isinstance(json_data, dict) and 'error' in json_data:
                    error_value = json_data.get('error')
                    if error_value is True:
                        print(f" [error=True]", end=" ")
                if isinstance(json_data, dict) and 'data' in json_data:
                    data_content = json_data.get('data', [])
                    if isinstance(data_content, list):
                        print(f" [data: {len(data_content)} items]", end=" ")
                        if len(data_content) > 0:
                            print(f" ✓", end=" ")
                    elif data_content is None:
                        print(f" [data: None]", end=" ")
                    else:
                        print(f" [data: {type(data_content).__name__}]", end=" ")
            
            parsed_data = parse_proposal_data(json_data, timestamp)
            if parsed_data:
                all_data.extend(parsed_data)
                successful += 1
                print(f"✓ {len(parsed_data)} proposals found")
            else:
                empty_responses += 1
                print("(no proposals this week)")
        else:
            failed += 1
            print("✗ Request error")
        
        if i < len(timestamps):
            time.sleep(REQUEST_DELAY)
        
        if i % 10 == 0 and all_data:
            temp_df = pd.DataFrame(all_data)
            temp_file = str(OUTPUT_FILE).replace('.csv', '_partial.csv')
            temp_df.to_csv(temp_file, index=False)
            print(f"  [Progress] {len(all_data)} records collected so far (saved to {temp_file})")
    
    print("\n" + "=" * 60)
    print("Collection summary:")
    print(f"  Weeks with data: {successful}")
    print(f"  Empty weeks (no proposals): {empty_responses}")
    print(f"  Weeks with error: {failed}")
    print(f"  Total records collected: {len(all_data)}")
    print("=" * 60)
    
    if all_data:
        df = pd.DataFrame(all_data)
        
        initial_count = len(df)
        df = df.drop_duplicates(subset=['proposal_hash', 'week_timestamp'], keep='first')
        duplicates_removed = initial_count - len(df)
        
        if duplicates_removed > 0:
            print(f"\nRemoved {duplicates_removed} duplicates")
        
        df = df.sort_values('week_timestamp', ascending=False)
        
        df.to_csv(str(OUTPUT_FILE), index=False)
        
        print("\n" + "=" * 60)
        print("Collection completed!")
        print(f"Total unique records: {len(df)}")
        print(f"File saved to: {OUTPUT_FILE}")
        print("=" * 60)
        
        if len(df) > 0:
            print("\nData preview (first 10 rows):")
            print(df.head(10).to_string())
            
            print("\nStatistics:")
            print(f"  Period: {df['week_date'].min()} to {df['week_date'].max()}")
            print(f"  Unique pools: {df['derived_pool_address'].nunique()}")
            print(f"  Unique proposals: {df['proposal_hash'].nunique()}")
            print(f"  Weeks with data: {df['week_date'].nunique()}")
    else:
        print("\n" + "=" * 60)
        print("⚠ No data was collected.")
        print("\nPossible causes:")
        print("  1. The API may not have data for the specified period")
        print("  2. The timestamp format may be incorrect")
        print("  3. Connection or rate limiting issues")
        print("\nSuggestions:")
        print("  - Check if data is available on the HiddenHand website")
        print(f"  - Verify if the initial timestamp ({START_TIMESTAMP}) is correct")
        print("=" * 60)


if __name__ == "__main__":
    main()
