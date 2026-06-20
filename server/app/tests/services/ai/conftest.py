from datetime import datetime

import pytest


@pytest.fixture
def fixed_now() -> datetime:
    """A fixed Tuesday reference time, so 'next Friday' etc. always resolve
    to the same date regardless of when the test suite actually runs."""
    return datetime(2026, 6, 16, 9, 0, 0)  
