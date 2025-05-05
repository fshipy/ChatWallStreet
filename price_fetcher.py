import os
import yfinance as yf
import httpx
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default to yfinance if no provider is specified
PRICE_PROVIDER = os.getenv("PRICE_PROVIDER", "yfinance")

# API keys (if using Alpha Vantage or IEX Cloud)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
IEX_CLOUD_API_KEY = os.getenv("IEX_CLOUD_API_KEY", "")

async def fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch current prices for a list of symbols.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    if PRICE_PROVIDER == "alpha_vantage":
        return await fetch_prices_alpha_vantage(symbols)
    elif PRICE_PROVIDER == "iex_cloud":
        return await fetch_prices_iex_cloud(symbols)
    else:
        # Default to yfinance
        return fetch_prices_yfinance(symbols)

def fetch_prices_yfinance(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch prices using yfinance.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    prices = {}
    
    # Batch fetch data for all symbols
    data = yf.download(symbols, period="1d", progress=False)
    
    # If only one symbol is requested, the structure is different
    if len(symbols) == 1:
        prices[symbols[0]] = data["Close"].iloc[-1]
    else:
        # Extract the latest closing price for each symbol
        for symbol in symbols:
            try:
                # Handle if the symbol wasn't found
                if symbol in data["Close"]:
                    prices[symbol] = data["Close"][symbol].iloc[-1]
                else:
                    prices[symbol] = 0.0
            except Exception:
                prices[symbol] = 0.0
    
    return prices

async def fetch_prices_alpha_vantage(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch prices using Alpha Vantage API.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("Alpha Vantage API key is required but not provided")
    
    prices = {}
    
    async with httpx.AsyncClient() as client:
        for symbol in symbols:
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
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

async def fetch_prices_iex_cloud(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch prices using IEX Cloud API.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        Dictionary mapping symbols to their current prices
    """
    if not IEX_CLOUD_API_KEY:
        raise ValueError("IEX Cloud API key is required but not provided")
    
    prices = {}
    
    # Convert symbols list to comma-separated string
    symbols_str = ",".join(symbols)
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"https://cloud.iexapis.com/stable/stock/market/batch?symbols={symbols_str}&types=quote&token={IEX_CLOUD_API_KEY}"
            response = await client.get(url)
            data = response.json()
            
            # Extract prices for each symbol
            for symbol in symbols:
                if symbol in data and "quote" in data[symbol] and "latestPrice" in data[symbol]["quote"]:
                    prices[symbol] = float(data[symbol]["quote"]["latestPrice"])
                else:
                    prices[symbol] = 0.0
        except Exception:
            # Default to 0 for any failures
            for symbol in symbols:
                prices[symbol] = 0.0
    
    return prices

async def get_portfolio_values(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich holdings with current prices and calculate values.
    
    Args:
        holdings: List of holdings (with symbol and shares)
        
    Returns:
        Holdings enriched with price and value
    """
    # Extract unique symbols
    symbols = list(set(h["symbol"] for h in holdings))
    
    # Fetch prices for all symbols
    prices = await fetch_prices(symbols)
    
    # Enrich holdings with price and value
    enriched_holdings = []
    
    for holding in holdings:
        symbol = holding["symbol"]
        shares = holding["shares"]
        price = prices.get(symbol, 0.0)
        value = shares * price
        
        enriched = {**holding, "price": price, "value": value}
        enriched_holdings.append(enriched)
    
    return enriched_holdings 