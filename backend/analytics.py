"""Dashboard, alerts and report tables derived only from PostgreSQL rows."""
from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from backend.config import get_demo_today
from backend.coordination_queries import request_payload
from backend.models import CoordinationRequest
from backend.queries import query_cases, query_overlaps

STATUSES = ("pending", "under_process", "escalated", "transferred", "disposed")
REPORT_TYPES = (
    "institution-wise", "bureau-wise", "region-wise", "status-wise",
    "ageing-buckets", "disposal-rate", "overlapping-cases",
)
AGE_BUCKETS = (("0-7 days", 0, 7), ("8-30 days", 8, 30),
               ("31-60 days", 31, 60), ("61-90 days", 61, 90), ("91+ days", 91, None))


def status_counts(rows):
    counts = Counter(row["status"] for row in rows)
    return {"total": len(rows), **{status: counts[status] for status in STATUSES},
            "open": len(rows) - counts["disposed"]}


def group_counts(rows, field):
    groups = {}
    for row in rows:
        label = row[field] or "Unknown"
        groups.setdefault(label, []).append(row)
    return [{field: label, **status_counts(group)} for label, group in sorted(groups.items())]


def institution_counts(rows):
    groups = {}
    for row in rows:
        # Each unresolved record is separate; similar names never group identities.
        key = ("institution", row["institution_id"]) if row["identity_resolved"] and row["institution_id"] else ("unresolved", row["id"])
        groups.setdefault(key, []).append(row)
    result = []
    for group in groups.values():
        first = group[0]
        result.append({
            "institution_id": first["institution_id"], "aicte_id": first["aicte_id"],
            "institution_name": first["institution_name"], "region": first["region"],
            "identity_resolved": first["identity_resolved"],
            "unresolved_case_code": None if first["identity_resolved"] else first["case_code"],
            **status_counts(group),
        })
    return sorted(result, key=lambda row: (row["aicte_id"] is None, row["aicte_id"] or row["unresolved_case_code"]))


def case_flags(rows, today):
    opened = [row for row in rows if row["status"] != "disposed"]
    due_end = today + timedelta(days=7)
    return {
        "pending_too_long": [{**row, "age_days": (today - row["received_on"]).days}
                             for row in rows if row["status"] == "pending" and row["received_on"] < today - timedelta(days=30)],
        "due_within_7_days": [{**row, "days_until_due": (row["expected_disposal_on"] - today).days}
                              for row in opened if row["expected_disposal_on"] is not None and today <= row["expected_disposal_on"] <= due_end],
        "overdue": [{**row, "days_overdue": (today - row["expected_disposal_on"]).days}
                    for row in opened if row["expected_disposal_on"] is not None and row["expected_disposal_on"] < today],
        "escalated": [row for row in rows if row["status"] == "escalated"],
    }


def dashboard_summary(db):
    today = get_demo_today()
    rows = query_cases(db)
    flags = case_flags(rows, today)
    return {
        "as_of": today, **status_counts(rows),
        "overdue": len(flags["overdue"]), "due_within_7_days": len(flags["due_within_7_days"]),
        "unresolved_cases": sum(not row["identity_resolved"] for row in rows),
        "bureau_wise": group_counts(rows, "bureau"),
        "region_wise": group_counts(rows, "region"),
        "institution_wise": institution_counts(rows),
    }


def alerts(db):
    today = get_demo_today()
    rows = query_cases(db)
    unacknowledged = db.scalars(select(CoordinationRequest).where(
        CoordinationRequest.status == "requested",
        CoordinationRequest.acknowledged_at.is_(None),
        CoordinationRequest.follow_up_on.is_not(None),
        CoordinationRequest.follow_up_on < today,
    ).order_by(CoordinationRequest.follow_up_on, CoordinationRequest.id))
    return {
        "as_of": today, "overlap": query_overlaps(db), **case_flags(rows, today),
        "unacknowledged": [{**request_payload(db, request),
                             "days_past_follow_up": (today - request.follow_up_on).days}
                            for request in unacknowledged],
    }


def report(db, report_type):
    if report_type not in REPORT_TYPES:
        raise ValueError("Unknown report type")
    today = get_demo_today()
    cases = query_cases(db)
    count_columns = ["total", *STATUSES, "open"]
    if report_type == "institution-wise":
        columns = ["institution_id", "aicte_id", "institution_name", "region",
                   "identity_resolved", "unresolved_case_code", *count_columns]
        rows = institution_counts(cases)
    elif report_type in ("bureau-wise", "region-wise"):
        field = "bureau" if report_type == "bureau-wise" else "region"
        columns, rows = [field, *count_columns], group_counts(cases, field)
    elif report_type == "status-wise":
        counts = Counter(row["status"] for row in cases)
        columns = ["status", "total"]
        rows = [{"status": status, "total": counts[status]} for status in STATUSES]
    elif report_type == "ageing-buckets":
        columns = ["bucket", "min_days", "max_days", "total"]
        ages = [max(0, (today - row["received_on"]).days) for row in cases if row["status"] != "disposed"]
        rows = [{"bucket": name, "min_days": low, "max_days": high,
                 "total": sum(low <= age and (high is None or age <= high) for age in ages)}
                for name, low, high in AGE_BUCKETS]
    elif report_type == "disposal-rate":
        columns = ["bureau", "total", "disposed", "disposal_rate_percent"]
        groups = [{"bureau": "All", **status_counts(cases)}, *group_counts(cases, "bureau")]
        rows = [{"bureau": group["bureau"], "total": group["total"], "disposed": group["disposed"],
                 "disposal_rate_percent": round(100 * group["disposed"] / group["total"], 2) if group["total"] else 0.0}
                for group in groups]
    else:
        columns = ["aicte_id", "institution_name", "case_code", "bureau", "status", "officer", "message"]
        rows = [{"aicte_id": overlap["aicte_id"], "institution_name": overlap["institution_name"],
                 **{key: case[key] for key in ("case_code", "bureau", "status", "officer")},
                 "message": overlap["message"]}
                for overlap in query_overlaps(db) for case in overlap["cases"]]
    return {"type": report_type, "as_of": today, "columns": columns, "rows": rows}
