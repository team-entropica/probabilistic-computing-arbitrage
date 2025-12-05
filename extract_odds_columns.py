#!/usr/bin/env python3
"""
Script to extract odds columns from the history section of the JSON file.
For each sub-object in history, extracts the value at index 1 (the actual odd)
from each array in the 'home', 'draw', 'away' arrays.
"""

import json
import sys
from pathlib import Path


def extract_odds_columns(json_file_path):
    """
    Extract odds columns from the history section.
    
    Args:
        json_file_path: Path to the JSON file
        
    Returns:
        Dictionary with column names as keys and lists of odds as values
    """
    # Load the JSON file
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Navigate to the history section
    # Assuming we want the first event and first period (num_0)
    if 'events' not in data or len(data['events']) == 0:
        raise ValueError("No events found in JSON file")
    
    event = data['events'][0]
    
    if 'periods' not in event:
        raise ValueError("No periods found in event")
    
    # Find the first period with a history section
    history = None
    period_key = None
    
    for key, period in event['periods'].items():
        if 'history' in period and period['history']:
            history = period['history']
            period_key = key
            break
    
    if history is None:
        raise ValueError("No history section found in any period")
    
    print(f"Processing history from period: {period_key}", file=sys.stderr)
    
    # Extract columns for each sub-object in history
    columns = {}
    
    # Process each key in history (e.g., "moneyline", "spreads", "totals")
    for history_key, history_value in history.items():
        if not isinstance(history_value, dict):
            continue
        
        # Handle moneyline (direct structure: home, draw, away)
        if history_key == 'moneyline':
            sub_key_order = ['home', 'draw', 'away']
            sub_key_mapping = {
                'home': 'money_line_home',
                'draw': 'money_line_draw',
                'away': 'money_line_away'
            }
            
            for sub_key in sub_key_order:
                if sub_key not in history_value:
                    continue
                    
                sub_array = history_value[sub_key]
                if not isinstance(sub_array, list):
                    continue
                
                column_name = sub_key_mapping.get(sub_key, f"{history_key}_{sub_key}")
                
                # Extract value at index 1 from each sub-array
                odds_values = []
                for item in sub_array:
                    if isinstance(item, list) and len(item) > 1:
                        odds_values.append(item[1])
                
                columns[column_name] = odds_values
                print(f"Extracted {len(odds_values)} values for column: {column_name}", file=sys.stderr)
        
        # Handle spreads (nested structure: spread_value -> home/away)
        elif history_key == 'spreads':
            # Sort spread keys to maintain consistent order
            spread_keys = sorted(history_value.keys(), key=lambda x: float(x) if x.replace('-', '').replace('.', '').isdigit() else 0)
            
            for spread_key, spread_data in history_value.items():
                if not isinstance(spread_data, dict):
                    continue
                
                # Process home and away for each spread
                for side in ['home', 'away']:
                    if side not in spread_data:
                        continue
                    
                    sub_array = spread_data[side]
                    if not isinstance(sub_array, list):
                        continue
                    
                    # Create column name: spread_-0.75_home, spread_-0.75_away, etc.
                    column_name = f"spread_{spread_key}_{side}"
                    
                    # Extract value at index 1 from each sub-array
                    odds_values = []
                    for item in sub_array:
                        if isinstance(item, list) and len(item) > 1:
                            odds_values.append(item[1])
                    
                    columns[column_name] = odds_values
                    print(f"Extracted {len(odds_values)} values for column: {column_name}", file=sys.stderr)
        
        # Handle totals (nested structure: total_value -> over/under)
        elif history_key == 'totals':
            # Sort total keys to maintain consistent order
            total_keys = sorted(history_value.keys(), key=lambda x: float(x) if x.replace('.', '').isdigit() else 0)
            
            for total_key, total_data in history_value.items():
                if not isinstance(total_data, dict):
                    continue
                
                # Process over and under for each total
                for side in ['over', 'under']:
                    if side not in total_data:
                        continue
                    
                    sub_array = total_data[side]
                    if not isinstance(sub_array, list):
                        continue
                    
                    # Create column name: totals_3.25_over, totals_3.25_under, etc.
                    column_name = f"totals_{total_key}_{side}"
                    
                    # Extract value at index 1 from each sub-array
                    odds_values = []
                    for item in sub_array:
                        if isinstance(item, list) and len(item) > 1:
                            odds_values.append(item[1])
                    
                    columns[column_name] = odds_values
                    print(f"Extracted {len(odds_values)} values for column: {column_name}", file=sys.stderr)
        
        # Handle any other history keys generically
        else:
            # Try to process as direct structure (like moneyline)
            for sub_key, sub_array in history_value.items():
                if not isinstance(sub_array, list):
                    continue
                
                column_name = f"{history_key}_{sub_key}"
                
                # Extract value at index 1 from each sub-array
                odds_values = []
                for item in sub_array:
                    if isinstance(item, list) and len(item) > 1:
                        odds_values.append(item[1])
                
                columns[column_name] = odds_values
                print(f"Extracted {len(odds_values)} values for column: {column_name}", file=sys.stderr)
    
    return columns


def output_columns(columns, output_format='csv', output_file=None):
    """
    Output the columns in the specified format.
    
    Args:
        columns: Dictionary with column names and values
        output_format: 'csv' or 'json'
        output_file: Optional file path to write output to. If None, prints to stdout.
    """
    # Determine output stream
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    
    try:
        if output_format == 'csv':
            # Get all column names in a logical order
            # Order: money_line columns first, then spreads, then totals, then others
            preferred_order = ['money_line_home', 'money_line_draw', 'money_line_away']
            column_names = []
            
            # Add moneyline columns first
            for col in preferred_order:
                if col in columns:
                    column_names.append(col)
            
            # Add spread columns (sorted by spread value, then by side: home before away)
            spread_cols = [col for col in columns.keys() if col.startswith('spread_')]
            def spread_sort_key(x):
                parts = x.split('_')
                if len(parts) >= 2:
                    try:
                        spread_val = float(parts[1])
                        side_order = 0 if parts[2] == 'home' else 1
                        return (spread_val, side_order)
                    except (ValueError, IndexError):
                        return (0, 0)
                return (0, 0)
            spread_cols.sort(key=spread_sort_key)
            column_names.extend(spread_cols)
            
            # Add totals columns (sorted by total value, then by side: over before under)
            totals_cols = [col for col in columns.keys() if col.startswith('totals_')]
            def totals_sort_key(x):
                parts = x.split('_')
                if len(parts) >= 2:
                    try:
                        total_val = float(parts[1])
                        side_order = 0 if parts[2] == 'over' else 1
                        return (total_val, side_order)
                    except (ValueError, IndexError):
                        return (0, 0)
                return (0, 0)
            totals_cols.sort(key=totals_sort_key)
            column_names.extend(totals_cols)
            
            # Add any other columns that weren't in the preferred order
            for col in sorted(columns.keys()):
                if col not in column_names:
                    column_names.append(col)
            
            # Find the maximum length to pad shorter columns
            max_length = max(len(columns[col]) for col in column_names) if column_names else 0
            
            # Print header
            f.write(','.join(column_names) + '\n')
            
            # Print rows
            for i in range(max_length):
                row = []
                for col in column_names:
                    if i < len(columns[col]):
                        row.append(str(columns[col][i]))
                    else:
                        row.append('')
                f.write(','.join(row) + '\n')
        
        elif output_format == 'json':
            f.write(json.dumps(columns, indent=2))
        
        else:
            raise ValueError(f"Unknown output format: {output_format}")
    
    finally:
        if output_file and f:
            f.close()
            print(f"Output saved to: {output_file}", file=sys.stderr)


def main():
    # Default file path
    default_file = Path(__file__).parent / "src" / "example-data" / "barcelona-vs-atletico.json"
    
    # Get file path from command line or use default
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
    else:
        json_file = default_file
    
    if not json_file.exists():
        print(f"Error: File not found: {json_file}", file=sys.stderr)
        sys.exit(1)
    
    # Get output format from command line or use default (csv)
    output_format = sys.argv[2] if len(sys.argv) > 2 else 'csv'
    
    # Get output file from command line (optional)
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        # Extract columns
        columns = extract_odds_columns(json_file)
        
        # Output the columns
        output_columns(columns, output_format, output_file)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

