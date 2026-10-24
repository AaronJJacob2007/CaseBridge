"""Slice 4 read-only analytics and downloadable CSV reports."""
import csv
from io import StringIO

from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder

from backend.analytics import REPORT_TYPES, alerts, dashboard_summary, report
from backend.case_routes import Database

router = APIRouter()


def get_report(db, report_type):
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown report type")
    return report(db, report_type)


def safe_csv_cell(value):
    # Prevent spreadsheet formulas in untrusted text fields; numbers stay numeric.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.get("/dashboard/summary")
def get_dashboard(db: Database):
    return dashboard_summary(db)


@router.get("/alerts")
def get_alerts(db: Database):
    return alerts(db)


# Register the suffix route before the generic route.
@router.get("/reports/{report_type}.csv")
def get_report_csv(report_type: str, db: Database):
    data = jsonable_encoder(get_report(db, report_type))
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=data["columns"])
    writer.writeheader()
    writer.writerows({key: safe_csv_cell(row.get(key)) for key in data["columns"]} for row in data["rows"])
    return Response(content=output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="casebridge-{report_type}.csv"'})


@router.get("/reports/{report_type}")
def get_report_json(report_type: str, db: Database):
    return get_report(db, report_type)
