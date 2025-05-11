"""
Symbol mapping configuration for different data providers.
This file contains mappings to handle different symbol representations across various data sources.
"""

# Dictionary mapping standard symbols to their provider-specific representations
SYMBOL_MAPPINGS = {
    # Yahoo Finance specific mappings
    'yfinance': {
        'BRKB': 'BRK-B',
        'BRK B': 'BRK-B',
        'BRK.B': 'BRK-B',  # Berkshire Hathaway Class B
        'BRK.BR': 'BRK-BR',  # Brookfield Asset Management
        'BRK.A': 'BRK-A',  # Berkshire Hathaway Class A
    },
    
    # Alpha Vantage specific mappings
    'alpha_vantage': {
        'BRK.B': 'BRK.B',
        'BRK.BR': 'BRK.BR',
        'BRK.A': 'BRK.A',
    },
    
    # IEX Cloud specific mappings
    'iex_cloud': {
        'BRK.B': 'BRK.B',
        'BRK.BR': 'BRK.BR',
        'BRK.A': 'BRK.A',
    }
}

def get_provider_symbol(symbol: str, provider: str) -> str:
    """
    Get the provider-specific symbol representation for a given symbol.
    
    Args:
        symbol: The standard symbol representation
        provider: The data provider ('yfinance', 'alpha_vantage', or 'iex_cloud')
        
    Returns:
        The provider-specific symbol representation
    """
    if provider not in SYMBOL_MAPPINGS:
        return symbol
        
    return SYMBOL_MAPPINGS[provider].get(symbol, symbol) 