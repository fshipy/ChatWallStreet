import csv
import os
import datetime
from typing import List, Dict, Any, Optional
import re

# Define the structure of our holdings CSV
HOLDINGS_CSV_PATH = "data/holdings.csv"
HOLDINGS_HEADERS = ["symbol", "tag", "shares", "last_updated"]

def ensure_data_directory():
    """Ensure data directory and CSV files exist."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    
    # Create holdings.csv if it doesn't exist
    if not os.path.exists(HOLDINGS_CSV_PATH):
        with open(HOLDINGS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(HOLDINGS_HEADERS)

def read_holdings() -> List[Dict[str, Any]]:
    """Read all holdings from CSV file."""
    ensure_data_directory()
    
    holdings = []
    with open(HOLDINGS_CSV_PATH, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert shares to float
            if 'shares' in row:
                row['shares'] = float(row['shares'])
            holdings.append(row)
    
    return holdings

def update_holdings(positions: List[Dict[str, Any]], tag: str):
    """
    Update holdings by removing existing entries with the same tag
    and adding new entries.
    
    Args:
        positions: List of position dicts with 'symbol' and 'shares'
        tag: Tag to associate with these positions
    """
    ensure_data_directory()
    
    # Read existing holdings
    holdings = read_holdings()
    
    # Filter out entries with the given tag
    holdings = [h for h in holdings if h.get('tag') != tag]
    
    # Add new positions with timestamp
    timestamp = datetime.datetime.now().isoformat()
    for position in positions:
        holdings.append({
            "symbol": position["symbol"],
            "tag": tag,
            "shares": position["shares"],
            "last_updated": timestamp
        })
    
    # Write back to CSV
    write_holdings(holdings)

def write_holdings(holdings: List[Dict[str, Any]]):
    """Write holdings to CSV file."""
    ensure_data_directory()
    
    with open(HOLDINGS_CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HOLDINGS_HEADERS)
        writer.writeheader()
        writer.writerows(holdings)

def edit_holding(symbol: str, tag: str, shares: float):
    """
    Edit a specific holding by symbol and tag.
    If it exists, update shares; if not, add a new entry.
    
    Args:
        symbol: Stock symbol
        tag: Tag to identify the holding category
        shares: Number of shares
    """
    ensure_data_directory()
    
    holdings = read_holdings()
    timestamp = datetime.datetime.now().isoformat()
    
    # Try to find and update the existing entry
    found = False
    for holding in holdings:
        if holding['symbol'] == symbol and holding['tag'] == tag:
            holding['shares'] = shares
            holding['last_updated'] = timestamp
            found = True
            break
    
    # If not found, add a new entry
    if not found:
        holdings.append({
            "symbol": symbol,
            "tag": tag,
            "shares": shares,
            "last_updated": timestamp
        })
    
    write_holdings(holdings)

def filter_holdings(
    holdings: List[Dict[str, Any]], 
    include_tags: Optional[List[str]] = None, 
    exclude_tags: Optional[List[str]] = None,
    hide_options: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter holdings by tags to include or exclude, and optionally hide options (symbols ending with numbers).
    
    Args:
        holdings: List of holdings
        include_tags: List of tags to include (if None, include all)
        exclude_tags: List of tags to exclude
        hide_options: Whether to hide options (symbols ending with numbers)
        
    Returns:
        Filtered list of holdings
    """
    filtered = holdings
    
    if include_tags:
        filtered = [h for h in filtered if h.get('tag') in include_tags]
    
    if exclude_tags:
        filtered = [h for h in filtered if h.get('tag') not in exclude_tags]
    
    if hide_options:
        filtered = [h for h in filtered if not re.search(r'\d+$', str(h.get('symbol', '')))]
    
    return filtered

def group_by_symbol(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group holdings by symbol, aggregating shares across tags.
    
    Args:
        holdings: List of holdings
        
    Returns:
        List of aggregated holdings by symbol
    """
    symbol_map = {}
    
    for holding in holdings:
        symbol = holding.get('symbol')
        shares = holding.get('shares', 0)
        
        if symbol not in symbol_map:
            symbol_map[symbol] = {
                'symbol': symbol,
                'shares': shares,
                'tags': [holding.get('tag')],
                'last_updated': holding.get('last_updated')
            }
        else:
            symbol_map[symbol]['shares'] += shares
            if holding.get('tag') not in symbol_map[symbol]['tags']:
                symbol_map[symbol]['tags'].append(holding.get('tag'))
            
            # Use the most recent update time
            if holding.get('last_updated') > symbol_map[symbol]['last_updated']:
                symbol_map[symbol]['last_updated'] = holding.get('last_updated')
    
    return list(symbol_map.values()) 