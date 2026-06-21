"""
Duration parser for task estimation.

This module provides a robust duration parser that can handle various natural language
inputs for task duration estimation, making it more flexible and user-friendly than
the rigid string-matching approach used in the current implementation.
"""

import re
from typing import Optional, Union

# Common duration patterns and their hour equivalents
_DURATION_PATTERNS = {
    # Exact matches
    '15m': 0.25,
    '15 minutes': 0.25,
    '30m': 0.5,
    '30 minutes': 0.5,
    '45m': 0.75,
    '45 minutes': 0.75,
    '1h': 1.0,
    '1 hour': 1.0,
    '2h': 2.0,
    '2 hours': 2.0,
    'half day': 4.0,
    'half-day': 4.0,
    'half a day': 4.0,
    'full day': 8.0,
    'full-day': 8.0,
    'full a day': 8.0,
    
    # Natural language patterns
    'quick': 0.5,
    'short': 1.0,
    'small': 1.0,
    'big': 6.0,
    'huge': 10.0,
    'massive': 12.0,
    
    # Common abbreviations
    'q': 0.5,
    's': 1.0,
    'b': 6.0,
    'h': 10.0,
}

# Regular expressions for parsing
_HOURS_RE = re.compile(r'(?P<value>\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b', re.IGNORECASE)
_MINUTES_RE = re.compile(r'(?P<value>\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b', re.IGNORECASE)
_NUMBER_RE = re.compile(r'(?P<value>\d+(?:\.\d+)?)')
_UNIT_RE = re.compile(r'(?P<unit>h|m|hour|min)?$', re.IGNORECASE)

# Common duration keywords
_DURATION_KEYWORDS = {
    'minute': 1.0 / 60.0,
    'minutes': 1.0 / 60.0,
    'hour': 1.0,
    'hours': 1.0,
    'day': 8.0,
    'days': 8.0,
    'week': 40.0,
    'weeks': 40.0,
}


def parse_duration(duration_input: str) -> float:
    """
    Parse a duration input string and convert it to hours.
    
    This function handles a wide variety of natural language inputs for task duration,
    making it much more flexible and user-friendly than the rigid string-matching
    approach used in the current implementation.
    
    Args:
        duration_input: A string representing the duration (e.g., "1.5 hours", "45 minutes", "quick")
        
    Returns:
        Duration in hours (float)
        
    Examples:
        >>> parse_duration("15 minutes")
        0.25
        >>> parse_duration("1.5 hours")
        1.5
        >>> parse_duration("quick")
        0.5
        >>> parse_duration("2h")
        2.0
        >>> parse_duration("half day")
        4.0
    """
    if not duration_input or not duration_input.strip():
        return 2.0  # Default duration
    
    duration_str = duration_input.strip().lower()
    
    # Check for exact matches first (most efficient)
    if duration_str in _DURATION_PATTERNS:
        return _DURATION_PATTERNS[duration_str]
    
    # Check for common abbreviations
    if len(duration_str) == 1 and duration_str in _DURATION_PATTERNS:
        return _DURATION_PATTERNS[duration_str]
    
    # Try to match hours pattern (e.g., "1.5 hours", "2 hours")
    hours_match = _HOURS_RE.search(duration_str)
    if hours_match:
        return float(hours_match.group("value"))
    
    # Try to match minutes pattern (e.g., "90 minutes", "45 mins")
    minutes_match = _MINUTES_RE.search(duration_str)
    if minutes_match:
        minutes = float(minutes_match.group("value"))
        return minutes / 60.0
    
    # Try to match number with unit (e.g., "1.5h", "90m")
    number_match = _NUMBER_RE.search(duration_str)
    if number_match:
        val = float(number_match.group("value"))
        
        # Check if there's a unit after the number
        remaining = duration_str[number_match.end():].strip()
        if remaining:
            # Extract unit from remaining string
            unit_match = _UNIT_RE.search(remaining)
            if unit_match:
                unit = unit_match.group("unit")
                if unit and unit.startswith('m'):
                    return val / 60.0
                elif unit and unit.startswith('h'):
                    return val
        
        # No unit specified: assume minutes if > 10, else hours
        # This handles cases like "15" -> 0.25 hours, "120" -> 2 hours
        return val / 60.0 if val > 10 else val
    
    # Check for duration keywords (e.g., "an hour", "two days")
    for keyword, hours in _DURATION_KEYWORDS.items():
        if keyword in duration_str:
            # Try to extract a number before the keyword
            pattern = rf'(\d+(?:\.\d+)?)\s*{keyword}'
            match = re.search(pattern, duration_str, re.IGNORECASE)
            if match:
                return float(match.group(1)) * hours
            # If no number, use the default for that keyword
            return hours
    
    # Check for fractional durations (e.g., "half hour", "quarter day")
    fractional_patterns = [
        (r'(?P<num>\d+)/(?P<den>\d+)\s*(?P<unit>hour|day|week)', lambda n, d, u: float(n) / float(d) * _DURATION_KEYWORDS.get(u, 1.0)),
        (r'(?P<frac>half|quarter|third|tenth)\s*(?P<unit>hour|day|week)', lambda f, u: {'half': 0.5, 'quarter': 0.25, 'third': 1/3, 'tenth': 0.1}[f] * _DURATION_KEYWORDS.get(u, 1.0)),
    ]
    
    for pattern, converter in fractional_patterns:
        match = re.search(pattern, duration_str, re.IGNORECASE)
        if match:
            return converter(*match.groups())
    
    # If all parsing attempts fail, return default
    return 2.0


def is_valid_duration(duration_hours: float) -> bool:
    """
    Check if a duration in hours is within valid bounds.
    
    Args:
        duration_hours: Duration in hours
        
    Returns:
        True if duration is valid, False otherwise
    """
    return 0.25 <= duration_hours <= 200.0


def format_duration(hours: float) -> str:
    """
    Format a duration in hours to a human-readable string.
    
    Args:
        hours: Duration in hours
        
    Returns:
        Formatted duration string
    """
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif hours < 8:
        if hours == int(hours):
            return f"{int(hours)} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours:.1f} hour{'s' if hours != 1 else ''}"
    else:
        days = hours / 8
        if days == int(days):
            return f"{int(days)} day{'s' if days != 1 else ''}"
        else:
            return f"{days:.1f} day{'s' if days != 1 else ''}"
