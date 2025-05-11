import os
import yfinance as yf
import httpx
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import time
import re
from threading import Lock
import storage
import logging
from config.symbol_mappings import get_provider_symbol
from config.symbol_groups import normalize_symbol, get_display_symbol

# Load environment variables
load_dotenv()

# Default to yfinance if no provider is specified
PRICE_PROVIDER = os.getenv("PRICE_PROVIDER", "yfinance")

# API keys (if using Alpha Vantage or IEX Cloud)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
IEX_CLOUD_API_KEY = os.getenv("IEX_CLOUD_API_KEY", "")

# Simple in-memory cache for prices
_price_cache = {}
_price_cache_lock = Lock()
CACHE_EXPIRY_SECONDS = 600  # 10 minutes

async def fetch_prices(symbols: List[str], skip_options: bool = True) -> Dict[str, float]:
    """
    Fetch current prices for a list of symbols.
    
    Args:
        symbols: List of stock symbols
        skip_options: If True, skip symbols that appear to be options (containing special characters)
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    # Filter out options if skip_options is True
    if skip_options:
        symbols = [s for s in symbols if not any(c in s for c in ['$', '^', '=', '&', '|', '(', ')'])]
    
    if PRICE_PROVIDER == "alpha_vantage":
        return await fetch_prices_alpha_vantage(symbols)
    elif PRICE_PROVIDER == "iex_cloud":
        return await fetch_prices_iex_cloud(symbols)
    else:
        # Default to yfinance
        return fetch_prices_yfinance(symbols)

def is_option(symbol):
    """
    Check if a symbol represents an option contract.
    
    Args:
        symbol: Stock symbol to check
        
    Returns:
        bool: True if symbol appears to be an option, False otherwise
    """
    # Check for symbols ending in numbers (e.g. "GOOG May16'25 145")
    if re.search(r'\d+$', symbol):
        return True
        
    # Check for symbols ending in CALL or PUT (case insensitive)
    if re.search(r'(CALL|PUT)$', symbol, re.IGNORECASE):
        return True
        
    return False

def fetch_prices_yfinance(symbols: List[str], skip_options: bool = True) -> Dict[str, float]:
    """
    Fetch prices using yfinance, with in-memory caching and retry logic.
    
    Args:
        symbols: List of stock symbols
        skip_options: If True, skip symbols that appear to be options (containing special characters)
    """
    prices = {}
    now = time.time()
    symbols_to_fetch = []
    max_retries = 3
    retry_delay = 1  # seconds

    # Check cache first
    with _price_cache_lock:
        for symbol in symbols:
            if skip_options and is_option(symbol):
                continue
            cache_entry = _price_cache.get(symbol)
            if cache_entry and now - cache_entry['timestamp'] < CACHE_EXPIRY_SECONDS:
                prices[symbol] = cache_entry['price']
            else:
                symbols_to_fetch.append(symbol)

    if symbols_to_fetch:
        # Map symbols to yfinance format
        mapped_symbols = [get_provider_symbol(symbol, 'yfinance') for symbol in symbols_to_fetch]
        attempt = 0
        while attempt < max_retries:
            try:
                data = yf.download(mapped_symbols, period="1d", progress=False)
                for original_symbol, mapped_symbol in zip(symbols_to_fetch, mapped_symbols):
                    try:
                        if mapped_symbol in data["Close"]:
                            price = float(data["Close"][mapped_symbol].iloc[-1])
                            if not (price > 0 and price < float('inf')):
                                price = 0.0
                            prices[original_symbol] = price
                        else:
                            price = 0.0
                            prices[original_symbol] = price
                    except Exception:
                        price = 0.0
                        prices[original_symbol] = price
                    # Update cache
                    with _price_cache_lock:
                        _price_cache[original_symbol] = {'price': price, 'timestamp': now}
                break  # Success, exit retry loop
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    logging.warning(f"Failed to fetch prices for {symbols_to_fetch} after {max_retries} attempts: {e}")
                    for symbol in symbols_to_fetch:
                        prices[symbol] = 0.0
                        with _price_cache_lock:
                            _price_cache[symbol] = {'price': 0.0, 'timestamp': now}
                else:
                    time.sleep(retry_delay)
    return prices

async def fetch_prices_alpha_vantage(symbols: List[str], skip_options: bool = True) -> Dict[str, float]:
    """
    Fetch prices using Alpha Vantage API.
    
    Args:
        symbols: List of stock symbols
        skip_options: If True, skip symbols that appear to be options (containing special characters)
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("Alpha Vantage API key is required but not provided")
    
    prices = {}
    
    async with httpx.AsyncClient() as client:
        for symbol in symbols:
            try:
                # Map symbol to Alpha Vantage format
                mapped_symbol = get_provider_symbol(symbol, 'alpha_vantage')
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={mapped_symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
                response = await client.get(url)
                data = response.json()
                
                # Extract the price
                if "Global Quote" in data and "05. price" in data["Global Quote"]:
                    prices[symbol] = float(data["Global Quote"]["05. price"])
                else:
                    prices[symbol] = 0.0
            except Exception:
                prices[symbol] = 0.0
    
    return prices

async def fetch_prices_iex_cloud(symbols: List[str], skip_options: bool = True) -> Dict[str, float]:
    """
    Fetch prices using IEX Cloud API.
    
    Args:
        symbols: List of stock symbols
        skip_options: If True, skip symbols that appear to be options (containing special characters)
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    if not IEX_CLOUD_API_KEY:
        raise ValueError("IEX Cloud API key is required but not provided")
    
    prices = {}
    
    # Map symbols to IEX Cloud format
    mapped_symbols = [get_provider_symbol(symbol, 'iex_cloud') for symbol in symbols]
    
    # Convert symbols list to comma-separated string
    symbols_str = ",".join(mapped_symbols)
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"https://cloud.iexapis.com/stable/stock/market/batch?symbols={symbols_str}&types=quote&token={IEX_CLOUD_API_KEY}"
            response = await client.get(url)
            data = response.json()
            
            # Extract prices for each symbol
            for original_symbol, mapped_symbol in zip(symbols, mapped_symbols):
                if mapped_symbol in data and "quote" in data[mapped_symbol] and "latestPrice" in data[mapped_symbol]["quote"]:
                    prices[original_symbol] = float(data[mapped_symbol]["quote"]["latestPrice"])
                else:
                    prices[original_symbol] = 0.0
        except Exception:
            # Default to 0 for any failures
            for symbol in symbols:
                prices[symbol] = 0.0
    
    return prices

async def get_portfolio_values(holdings: List[Dict[str, Any]], force_refresh: bool = False, skip_options: bool = True) -> List[Dict[str, Any]]:
    """
    Enrich holdings with current prices and calculate values.
    If force_refresh is False, use last_price from holdings if available.
    If force_refresh is True, fetch from API and update holdings and CSV.
    
    Args:
        holdings: List of holding dictionaries
        force_refresh: If True, fetch new prices from API
        skip_options: If True, skip symbols that appear to be options
    """
    import datetime
    now_iso = datetime.datetime.now().isoformat()
    # Group holdings by canonical symbol
    grouped = {}
    for h in holdings:
        canonical = normalize_symbol(h["symbol"])
        if canonical not in grouped:
            grouped[canonical] = {**h, "symbol": canonical, "shares": 0}
        grouped[canonical]["shares"] += h["shares"]
    symbols = list(grouped.keys())
    
    if force_refresh:
        # If force_refresh, fetch new prices for all symbols
        prices = await fetch_prices(symbols, skip_options)
        enriched_holdings = []
        for holding in grouped.values():
            symbol = holding["symbol"]
            shares = holding["shares"]
            price = prices.get(symbol, 0.0)
            value = shares * price
            
            # Update price in price CSV instead of holdings
            storage.update_price(symbol, price, now_iso)
            
            # Add price info to the enriched holding for the response
            holding["last_price"] = price
            holding["last_price_time"] = now_iso
            
            enriched = {**holding, "symbol": get_display_symbol(symbol), "price": price, "value": value}
            enriched_holdings.append(enriched)
        
        return enriched_holdings
    else:
        # If not force_refresh, identify symbols with missing or zero prices
        enriched_holdings = []
        symbols_to_fetch = []
        symbol_map = {}
        
        for holding in grouped.values():
            symbol = holding["symbol"]
            price = holding.get("last_price")
            
            # If price is None or 0, mark for fetching
            if price is None or price == 0:
                symbols_to_fetch.append(symbol)
                symbol_map[symbol] = holding
            else:
                # Use cached price
                shares = holding["shares"]
                value = shares * price
                enriched = {**holding, "symbol": get_display_symbol(symbol), "price": price, "value": value}
                enriched_holdings.append(enriched)
        
        # Only fetch prices for symbols with missing or zero prices
        if symbols_to_fetch:
            prices = await fetch_prices(symbols_to_fetch, skip_options)
            
            for symbol in symbols_to_fetch:
                holding = symbol_map[symbol]
                shares = holding["shares"]
                price = prices.get(symbol, 0.0)
                value = shares * price
                
                # Update price in price CSV
                storage.update_price(symbol, price, now_iso)
                
                # Add price info to the enriched holding for the response
                holding["last_price"] = price
                holding["last_price_time"] = now_iso
                
                enriched = {**holding, "symbol": get_display_symbol(symbol), "price": price, "value": value}
                enriched_holdings.append(enriched)
        
        return enriched_holdings

def clear_price_cache():
    with _price_cache_lock:
        _price_cache.clear() 