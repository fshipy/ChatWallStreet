import csv
import os
import datetime
from typing import List, Dict, Any, Optional
import re

# Define the structure of our CSV files
HOLDINGS_CSV_PATH = "data/holdings.csv"
PRICES_CSV_PATH = "data/prices.csv"
HOLDINGS_HEADERS = ["symbol", "tag", "shares", "last_updated"]
PRICES_HEADERS = ["symbol", "last_price", "last_price_time"]

def ensure_data_directory():
    """Ensure data directory and CSV files exist."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    
    # Create holdings.csv if it doesn't exist
    if not os.path.exists(HOLDINGS_CSV_PATH):
        with open(HOLDINGS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(HOLDINGS_HEADERS)
    
    # Create prices.csv if it doesn't exist
    if not os.path.exists(PRICES_CSV_PATH):
        with open(PRICES_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(PRICES_HEADERS)

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
    
    # Read prices and merge with holdings
    prices = read_prices()
    price_map = {p['symbol']: p for p in prices}
    
    for holding in holdings:
        symbol = holding['symbol']
        if symbol in price_map:
            price_data = price_map[symbol]
            holding['last_price'] = float(price_data['last_price']) if price_data['last_price'] not in (None, '', 'None') else None
            holding['last_price_time'] = price_data['last_price_time'] if price_data['last_price_time'] not in (None, '', 'None') else None
        else:
            holding['last_price'] = None
            holding['last_price_time'] = None
    
    return holdings

def read_prices() -> List[Dict[str, Any]]:
    """Read all price data from CSV file."""
    ensure_data_directory()
    
    prices = []
    with open(PRICES_CSV_PATH, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert last_price to float if present
            if 'last_price' in row and row['last_price'] not in (None, '', 'None'):
                row['last_price'] = float(row['last_price'])
            else:
                row['last_price'] = None
            prices.append(row)
    
    return prices

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
        
        # Update prices if provided in the position
        if "last_price" in position and position["last_price"] is not None:
            update_price(position["symbol"], position["last_price"], position.get("last_price_time"))
    
    # Write back to CSV
    write_holdings(holdings)

def write_holdings(holdings: List[Dict[str, Any]]):
    """Write holdings to CSV file."""
    ensure_data_directory()
    
    # Filter out price data to avoid writing to holdings CSV
    clean_holdings = []
    for h in holdings:
        clean_holding = {k: h.get(k, None) for k in HOLDINGS_HEADERS}
        clean_holdings.append(clean_holding)
    
    with open(HOLDINGS_CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HOLDINGS_HEADERS)
        writer.writeheader()
        for h in clean_holdings:
            writer.writerow(h)

def write_prices(prices: List[Dict[str, Any]]):
    """Write prices to CSV file."""
    ensure_data_directory()
    
    with open(PRICES_CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=PRICES_HEADERS)
        writer.writeheader()
        for p in prices:
            row = {k: p.get(k, None) for k in PRICES_HEADERS}
            writer.writerow(row)

def update_price(symbol: str, last_price: float, last_price_time=None):
    """
    Update price for a specific symbol.
    
    Args:
        symbol: Stock symbol
        last_price: Last price of the symbol
        last_price_time: Last price time of the symbol (default: current time)
    """
    ensure_data_directory()
    
    # Read existing prices
    prices = read_prices()
    
    # Set price time if not provided
    if last_price_time is None:
        last_price_time = datetime.datetime.now().isoformat()
    
    # Try to find and update the existing entry
    found = False
    for price in prices:
        if price['symbol'] == symbol:
            price['last_price'] = last_price
            price['last_price_time'] = last_price_time
            found = True
            break
    
    # If not found, add a new entry
    if not found:
        prices.append({
            "symbol": symbol,
            "last_price": last_price,
            "last_price_time": last_price_time
        })
    
    write_prices(prices)

def edit_holding(symbol: str, tag: str, shares: float, last_price=None, last_price_time=None):
    """
    Edit a specific holding by symbol and tag.
    If it exists, update shares; if not, add a new entry.
    
    Args:
        symbol: Stock symbol
        tag: Tag to identify the holding category
        shares: Number of shares
        last_price: Last price of the holding (optional)
        last_price_time: Last price time of the holding (optional)
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
    
    # Update price if provided
    if last_price is not None:
        update_price(symbol, last_price, last_price_time)
    
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
                'tag': holding.get('tag'),  # Keep the original tag
                'tags': [holding.get('tag')],  # Also maintain list of all tags
                'last_updated': holding.get('last_updated'),
                'last_price': holding.get('last_price'),
                'last_price_time': holding.get('last_price_time')
            }
        else:
            symbol_map[symbol]['shares'] += shares
            if holding.get('tag') not in symbol_map[symbol]['tags']:
                symbol_map[symbol]['tags'].append(holding.get('tag'))
            
            # Use the most recent update time
            if isinstance(holding.get('last_updated'), str) and isinstance(symbol_map[symbol].get('last_updated'), str) and holding.get('last_updated') > symbol_map[symbol].get('last_updated'):
                symbol_map[symbol]['last_updated'] = holding.get('last_updated')
    
    return list(symbol_map.values()) 