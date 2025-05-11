"""
Symbol group configuration for grouping equivalent symbols and setting display names.
"""

# Map all equivalent symbols to a canonical symbol
SYMBOL_GROUPS = {
    # Berkshire Hathaway Class B
    'BRK.B': {
        'aliases': ['BRK-B', 'BRK.B', 'BRK B', 'BRKB'],
        'display': 'BRK.B',
        'full_name': 'Berkshire Hathaway Inc. Class B'
    },
    # Add more groups as needed
}

# Build a reverse lookup for normalization
SYMBOL_ALIAS_TO_CANONICAL = {}
for canonical, group in SYMBOL_GROUPS.items():
    for alias in group['aliases']:
        SYMBOL_ALIAS_TO_CANONICAL[alias.upper()] = canonical

def normalize_symbol(symbol: str) -> str:
    """
    Normalize a symbol to its canonical form for grouping.
    """
    return SYMBOL_ALIAS_TO_CANONICAL.get(symbol.upper(), symbol)

def get_display_symbol(symbol: str) -> str:
    """
    Get the display symbol for a canonical symbol.
    """
    canonical = normalize_symbol(symbol)
    return SYMBOL_GROUPS.get(canonical, {}).get('display', canonical)

def get_full_name(symbol: str) -> str:
    """
    Get the full name for a canonical symbol.
    """
    canonical = normalize_symbol(symbol)
    return SYMBOL_GROUPS.get(canonical, {}).get('full_name', canonical) 