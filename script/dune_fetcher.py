"""
Module to fetch data from Dune and generate CSVs
"""
import csv
from pathlib import Path
from dune_client.client import DuneClient


def fetch_dune_query(api_key: str, query_id: int):
    """
    Fetches data from a Dune query
    
    Args:
        api_key: Dune API key
        query_id: Dune query ID
        
    Returns:
        List of dictionaries with query data
    """
    dune = DuneClient(api_key)
    query_result = dune.get_latest_result(query_id)
    
    if not query_result or not hasattr(query_result, 'result') or not query_result.result:
        return None
    
    result = query_result.result
    rows = result.rows if hasattr(result, 'rows') and result.rows else []
    
    return rows if rows else None


def save_to_csv(data: list, output_path: Path):
    """
    Saves data to a CSV file
    
    Args:
        data: List of dictionaries or lists with data
        output_path: Path where to save the CSV
        
    Returns:
        Number of rows saved
    """
    if not data:
        return 0
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        if isinstance(data[0], dict):
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(csvfile)
            writer.writerows(data)
    
    return len(data)


def fetch_and_save(api_key: str, query_id: int, output_filename: str, project_root: Path = None):
    """
    Fetches data from Dune and saves to CSV
    
    Args:
        api_key: Dune API key
        query_id: Dune query ID
        output_filename: Output CSV filename
        project_root: Project root directory (optional)
        
    Returns:
        Tuple (success: bool, rows: int, path: Path)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent
    
    output_path = project_root / "data" / output_filename
    
    try:
        print(f"Fetching query {query_id}...")
        data = fetch_dune_query(api_key, query_id)
        
        if data is None:
            print(f"  ⚠️  No data found for query {query_id}")
            return False, 0, output_path
        
        print(f"  ✓ Data obtained: {len(data)} rows")
        print(f"  Saving to: {output_path}")
        
        rows_saved = save_to_csv(data, output_path)
        
        print(f"  ✓ CSV generated successfully! ({rows_saved} rows)\n")
        return True, rows_saved, output_path
        
    except Exception as e:
        print(f"  ✗ Error processing query {query_id}: {e}\n")
        return False, 0, output_path
