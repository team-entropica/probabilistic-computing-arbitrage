#!/usr/bin/env python3
"""
Script to extract odds columns from the history section of the JSON file.
For each sub-object in history, extracts the value at index 1 (the actual odd)
from each array in the 'home', 'draw', 'away' arrays.
Each row is aligned by timestamp (index 0 of each array).
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def extract_odds_columns(json_file_path):
    """
    Extract odds columns from the history section, aligned by timestamp.
    
    Args:
        json_file_path: Path to the JSON file
        
    Returns:
        Tuple of (columns_dict, timestamps_set) where:
        - columns_dict: Dictionary with column names as keys and dicts of {timestamp: odds} as values
        - timestamps_set: Set of all unique timestamps across all columns
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
    # Store as {column_name: {timestamp: odds_value}}
    columns = {}
    all_timestamps = set()
    
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
                
                # Extract timestamp (index 0) and odds (index 1) from each sub-array
                timestamp_odds = {}
                for item in sub_array:
                    if isinstance(item, list) and len(item) > 1:
                        timestamp = item[0]
                        odds = item[1]
                        timestamp_odds[timestamp] = odds
                        all_timestamps.add(timestamp)
                
                columns[column_name] = timestamp_odds
                print(f"Extracted {len(timestamp_odds)} values for column: {column_name}", file=sys.stderr)
        
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
                    
                    # Extract timestamp (index 0) and odds (index 1) from each sub-array
                    timestamp_odds = {}
                    for item in sub_array:
                        if isinstance(item, list) and len(item) > 1:
                            timestamp = item[0]
                            odds = item[1]
                            timestamp_odds[timestamp] = odds
                            all_timestamps.add(timestamp)
                    
                    columns[column_name] = timestamp_odds
                    print(f"Extracted {len(timestamp_odds)} values for column: {column_name}", file=sys.stderr)
        
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
                    
                    # Extract timestamp (index 0) and odds (index 1) from each sub-array
                    timestamp_odds = {}
                    for item in sub_array:
                        if isinstance(item, list) and len(item) > 1:
                            timestamp = item[0]
                            odds = item[1]
                            timestamp_odds[timestamp] = odds
                            all_timestamps.add(timestamp)
                    
                    columns[column_name] = timestamp_odds
                    print(f"Extracted {len(timestamp_odds)} values for column: {column_name}", file=sys.stderr)
        
        # Handle any other history keys generically
        else:
            # Try to process as direct structure (like moneyline)
            for sub_key, sub_array in history_value.items():
                if not isinstance(sub_array, list):
                    continue
                
                column_name = f"{history_key}_{sub_key}"
                
                # Extract timestamp (index 0) and odds (index 1) from each sub-array
                timestamp_odds = {}
                for item in sub_array:
                    if isinstance(item, list) and len(item) > 1:
                        timestamp = item[0]
                        odds = item[1]
                        timestamp_odds[timestamp] = odds
                        all_timestamps.add(timestamp)
                
                columns[column_name] = timestamp_odds
                print(f"Extracted {len(timestamp_odds)} values for column: {column_name}", file=sys.stderr)
    
    return columns, all_timestamps


def filter_and_fill_data(columns, all_timestamps, column_names, min_values_per_row=20):
    """
    Filter rows with too few values and fill missing values using forward fill.
    
    Args:
        columns: Dictionary with column names as keys and {timestamp: odds} dicts as values
        all_timestamps: Set of all unique timestamps
        column_names: List of column names in order
        min_values_per_row: Minimum number of non-empty values required to keep a row
        
    Returns:
        Tuple of (filtered_data, fill_report) where:
        - filtered_data: List of rows (each row is a list of values)
        - fill_report: Dictionary with detailed information about what was filled
    """
    sorted_timestamps = sorted(all_timestamps)
    
    # Build initial data matrix
    initial_data = []
    for timestamp in sorted_timestamps:
        row = [timestamp]
        for col in column_names[1:]:  # Skip timestamp column
            if col in columns and timestamp in columns[col]:
                row.append(columns[col][timestamp])
            else:
                row.append(None)  # Use None for missing values
        initial_data.append(row)
    
    # Count non-empty values per row (excluding timestamp)
    row_value_counts = []
    for row in initial_data:
        non_empty_count = sum(1 for val in row[1:] if val is not None)
        row_value_counts.append(non_empty_count)
    
    # Filter rows with <= min_values_per_row non-empty values
    filtered_data = []
    filtered_timestamps = []
    removed_rows = []
    
    for i, (row, count) in enumerate(zip(initial_data, row_value_counts)):
        if count > min_values_per_row:
            filtered_data.append(row)
            filtered_timestamps.append(row[0])
        else:
            removed_rows.append({
                'timestamp': row[0],
                'non_empty_count': count,
                'index': i
            })
    
    print(f"Filtered out {len(removed_rows)} rows with {min_values_per_row} or fewer values", file=sys.stderr)
    print(f"Remaining rows: {len(filtered_data)}", file=sys.stderr)
    
    # Fill missing values using forward fill (carry forward last known value)
    fill_report = {
        'total_filled': 0,
        'by_column': {},
        'by_row': {},
        'removed_rows': removed_rows
    }
    
    # For each column (excluding timestamp), fill missing values
    for col_idx, col_name in enumerate(column_names[1:], start=1):
        last_known_value = None
        fills_in_column = []
        
        for row_idx, row in enumerate(filtered_data):
            if row[col_idx] is None:
                # Need to fill this value
                if last_known_value is not None:
                    # Use forward fill: carry forward the last known value
                    row[col_idx] = last_known_value
                    fills_in_column.append({
                        'row_index': row_idx,
                        'timestamp': filtered_timestamps[row_idx],
                        'filled_value': last_known_value,
                        'method': 'forward_fill'
                    })
                    fill_report['total_filled'] += 1
                    
                    # Track in by_row report
                    if row_idx not in fill_report['by_row']:
                        fill_report['by_row'][row_idx] = []
                    fill_report['by_row'][row_idx].append({
                        'column': col_name,
                        'filled_value': last_known_value,
                        'method': 'forward_fill'
                    })
            else:
                # Update last known value
                last_known_value = row[col_idx]
        
        # If there are still missing values at the beginning, use backward fill
        # Find first non-None value and fill backwards
        first_non_none_idx = None
        first_non_none_value = None
        for row_idx, row in enumerate(filtered_data):
            if row[col_idx] is not None:
                first_non_none_idx = row_idx
                first_non_none_value = row[col_idx]
                break
        
        if first_non_none_idx is not None and first_non_none_idx > 0:
            # Fill backwards from first known value
            for row_idx in range(first_non_none_idx - 1, -1, -1):
                if filtered_data[row_idx][col_idx] is None:
                    filtered_data[row_idx][col_idx] = first_non_none_value
                    fills_in_column.append({
                        'row_index': row_idx,
                        'timestamp': filtered_timestamps[row_idx],
                        'filled_value': first_non_none_value,
                        'method': 'backward_fill'
                    })
                    fill_report['total_filled'] += 1
                    
                    # Track in by_row report
                    if row_idx not in fill_report['by_row']:
                        fill_report['by_row'][row_idx] = []
                    fill_report['by_row'][row_idx].append({
                        'column': col_name,
                        'filled_value': first_non_none_value,
                        'method': 'backward_fill'
                    })
        
        fill_report['by_column'][col_name] = fills_in_column
    
    return filtered_data, fill_report


def generate_fill_report(fill_report, output_file, convert_to_date=False):
    """
    Generate a detailed report of the filling process.
    
    Args:
        fill_report: Dictionary with fill information
        output_file: Base output file path (report will be saved as {output_file}.fill_report.txt)
        convert_to_date: If True, convert timestamps to dates in report
    """
    if output_file:
        report_file = str(output_file) + '.fill_report.txt'
    else:
        report_file = None
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("DATA FILLING REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Summary
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Total values filled: {fill_report['total_filled']}")
    report_lines.append(f"Rows removed (≤20 values): {len(fill_report['removed_rows'])}")
    report_lines.append(f"Rows with fills: {len(fill_report['by_row'])}")
    report_lines.append("")
    
    # Removed rows
    if fill_report['removed_rows']:
        report_lines.append("REMOVED ROWS")
        report_lines.append("-" * 80)
        for removed in fill_report['removed_rows'][:10]:  # Show first 10
            timestamp = removed['timestamp']
            if convert_to_date:
                try:
                    dt = datetime.fromtimestamp(timestamp)
                    timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, OSError):
                    timestamp_str = str(timestamp)
            else:
                timestamp_str = str(timestamp)
            report_lines.append(f"  Timestamp: {timestamp_str}, Non-empty values: {removed['non_empty_count']}")
        if len(fill_report['removed_rows']) > 10:
            report_lines.append(f"  ... and {len(fill_report['removed_rows']) - 10} more rows")
        report_lines.append("")
    
    # Filling method explanation
    report_lines.append("FILLING METHOD EXPLANATION")
    report_lines.append("-" * 80)
    report_lines.append("Missing values are filled using the following strategy:")
    report_lines.append("  1. Forward Fill: For each column, missing values are filled with the")
    report_lines.append("     last known value from previous rows (carrying values forward in time).")
    report_lines.append("  2. Backward Fill: If values are missing at the beginning of a column,")
    report_lines.append("     they are filled with the first known value (carrying values backward).")
    report_lines.append("")
    report_lines.append("This ensures that each row maintains the most recent available odds value")
    report_lines.append("for each betting market, which is appropriate for time series data.")
    report_lines.append("")
    
    # By column breakdown
    report_lines.append("FILLS BY COLUMN")
    report_lines.append("-" * 80)
    for col_name, fills in sorted(fill_report['by_column'].items()):
        if fills:
            report_lines.append(f"\nColumn: {col_name}")
            report_lines.append(f"  Total fills: {len(fills)}")
            report_lines.append("  Sample fills (first 5):")
            for fill in fills[:5]:
                timestamp = fill['timestamp']
                if convert_to_date:
                    try:
                        dt = datetime.fromtimestamp(timestamp)
                        timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError):
                        timestamp_str = str(timestamp)
                else:
                    timestamp_str = str(timestamp)
                report_lines.append(f"    Row {fill['row_index']} (timestamp: {timestamp_str}): "
                                  f"filled {fill['filled_value']} using {fill['method']}")
            if len(fills) > 5:
                report_lines.append(f"  ... and {len(fills) - 5} more fills")
    
    # By row breakdown (sample)
    report_lines.append("")
    report_lines.append("FILLS BY ROW (Sample - first 10 rows with fills)")
    report_lines.append("-" * 80)
    sample_rows = sorted(fill_report['by_row'].items())[:10]
    for row_idx, fills in sample_rows:
        timestamp = None  # Will be set from data
        report_lines.append(f"\nRow {row_idx}:")
        for fill in fills:
            report_lines.append(f"  Column '{fill['column']}': filled {fill['filled_value']} using {fill['method']}")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    # Write report
    report_text = '\n'.join(report_lines)
    if report_file:
        with open(report_file, 'w') as f:
            f.write(report_text)
        print(f"Fill report saved to: {report_file}", file=sys.stderr)
    else:
        print(report_text, file=sys.stderr)


def output_columns(columns, all_timestamps, output_format='csv', output_file=None, convert_to_date=False):
    """
    Output the columns in the specified format, aligned by timestamp.
    Filters rows with 20 or fewer values and fills missing values.
    
    Args:
        columns: Dictionary with column names as keys and {timestamp: odds} dicts as values
        all_timestamps: Set of all unique timestamps
        output_format: 'csv' or 'json'
        output_file: Optional file path to write output to. If None, prints to stdout.
        convert_to_date: If True, convert Unix timestamps to ISO format dates
    """
    # Determine output stream
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    
    try:
        if output_format == 'csv':
            # Get all column names in a logical order
            # Order: time column first, then money_line columns, then spreads, then totals, then others
            preferred_order = ['money_line_home', 'money_line_draw', 'money_line_away']
            column_names = ['timestamp']  # Time column first
            
            # Add moneyline columns
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
            
            # Filter rows and fill missing values
            filtered_data, fill_report = filter_and_fill_data(columns, all_timestamps, column_names, min_values_per_row=20)
            
            # Generate fill report
            if output_file:
                generate_fill_report(fill_report, output_file, convert_to_date)
            
            # Print header
            f.write(','.join(column_names) + '\n')
            
            # Print rows from filtered and filled data
            for row in filtered_data:
                output_row = []
                
                # Add timestamp (convert to date if requested)
                timestamp = row[0]
                if convert_to_date:
                    try:
                        dt = datetime.fromtimestamp(timestamp)
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError):
                        time_str = str(timestamp)
                else:
                    time_str = str(timestamp)
                output_row.append(time_str)
                
                # Add odds values for each column (already filled)
                for val in row[1:]:  # Skip timestamp
                    if val is not None:
                        output_row.append(str(val))
                    else:
                        output_row.append('')  # Should not happen after filling, but just in case
                
                f.write(','.join(output_row) + '\n')
        
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
    
    # Check if user wants date conversion (--date flag)
    convert_to_date = '--date' in sys.argv or '-d' in sys.argv
    
    try:
        # Extract columns
        columns, all_timestamps = extract_odds_columns(json_file)
        
        # Output the columns
        output_columns(columns, all_timestamps, output_format, output_file, convert_to_date)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

