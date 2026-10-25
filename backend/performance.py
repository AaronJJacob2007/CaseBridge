"""Receipt-cohort reporting: current outcomes, never inferred disposal dates."""
from calendar import monthrange
from datetime import date

from fastapi import HTTPException

from backend.config import get_demo_today
from backend.queries import query_cases

RULES = ("Cases received counts receipt dates within the selected calendar month or quarter, "
         "through the reference date. Disposed and outstanding split that same receipt cohort "
         "by current saved status; outstanding means any status other than disposed. "
         "These are not disposals during the period or historical period-end backlog. "
         "Bureau attribution uses the currently assigned bureau. Unresolved cases are included.")


def performance_report(db, kind="monthly", year=None, period=None):
    today = get_demo_today()
    year = today.year if year is None else year
    period = (today.month if kind == "monthly" else (today.month - 1) // 3 + 1) if period is None else period
    if kind not in ("monthly", "quarterly") or not 1 <= year <= 9998 or not 1 <= period <= (12 if kind == "monthly" else 4):
        raise HTTPException(status_code=422, detail="Choose a valid year and month (1-12) or quarter (1-4)")
    month = period if kind == "monthly" else (period - 1) * 3 + 1
    end_month = month if kind == "monthly" else month + 2
    start = date(year, month, 1)
    end = date(year, end_month, monthrange(year, end_month)[1])
    if start > today:
        raise HTTPException(status_code=422, detail="The selected period starts after the reference date")
    through = min(end, today)
    cases = query_cases(db, received_from=start, received_to=through)
    rows = []
    for bureau in ("All", "PGRC", "RB", "OTHER"):
        cohort = cases if bureau == "All" else [case for case in cases if case["bureau"] == bureau]
        disposed = sum(case["status"] == "disposed" for case in cohort)
        rows.append({"period_start": start, "period_end": end,
                     "receipts_through": through, "status_as_of": today, "bureau": bureau,
                     "received": len(cohort), "disposed": disposed,
                     "outstanding": len(cohort) - disposed})
    return {"type": "performance", "as_of": today, "kind": kind, "year": year,
            "period": period, "partial_period": through < end, "counting_rules": RULES,
            "columns": list(rows[0]), "rows": rows}
