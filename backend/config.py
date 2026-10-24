"""One configurable source of today's date for all date-based business rules."""
import os
from datetime import date


def get_demo_today() -> date:
    return date.fromisoformat(os.environ.get("DEMO_TODAY", "2026-10-24"))
