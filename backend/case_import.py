"""Validate synthetic bureau CSV imports before writing any cases."""
import csv
from io import StringIO

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from backend.case_inputs import CaseCreate
from backend.case_service import create_case
from backend.models import Case, Institution

FIELDS = {'case_code', 'institution_name', 'aicte_id', 'raw_region', 'category', 'description',
          'received_on', 'status', 'remarks', 'next_action', 'expected_disposal_on'}
REQUIRED = {'case_code', 'institution_name'}


class ImportRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=500_000)


def inspect_import(db, actor, csv_text):
    if actor.role != 'officer':
        raise HTTPException(status_code=403, detail='Only bureau officers can import cases')
    try:
        reader = csv.DictReader(StringIO(csv_text.lstrip('\ufeff'), newline=''), strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not REQUIRED.issubset(headers) or set(headers) - FIELDS:
            raise HTTPException(status_code=422, detail='CSV needs case_code and institution_name headers; remove duplicate or unsupported columns')
        raw_rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail='Invalid CSV format') from exc
    if not raw_rows or len(raw_rows) > 200:
        raise HTTPException(status_code=422, detail='CSV must contain between 1 and 200 rows')
    known_codes = set(db.scalars(select(Case.case_code)).all())
    known_ids = set(db.scalars(select(Institution.aicte_id)).all())
    seen = set()
    results = []
    for index, row in enumerate(raw_rows, start=2):
        errors = []
        if None in row or any(value is None for value in row.values()):
            results.append({'row': index, 'case_code': '', 'institution_name': '', 'errors': ['Row has missing or extra columns'], 'warnings': []})
            continue
        data = {key: value.strip() for key, value in row.items() if value.strip()}
        code = data.get('case_code', '')
        if code and (code in known_codes or code in seen):
            errors.append('Duplicate case code')
        if code:
            seen.add(code)
        data.update(bureau=actor.bureau, officer_id=actor.id)
        try:
            parsed = CaseCreate.model_validate(data)
        except ValidationError as exc:
            parsed = None
            errors.extend('.'.join(str(part) for part in issue['loc']) + ': ' + issue['msg'] for issue in exc.errors())
        aicte_id = data.get('aicte_id')
        warnings = [] if aicte_id and aicte_id in known_ids else ['Institution ID is missing or unknown; identity will remain unresolved']
        results.append({'row': index, 'case_code': code, 'institution_name': data.get('institution_name', ''),
                        'errors': errors, 'warnings': warnings, '_parsed': parsed})
    return results


def import_preview(db, actor, text):
    rows = inspect_import(db, actor, text)
    return {'rows': [{key: value for key, value in row.items() if key != '_parsed'} for row in rows],
            'valid_count': sum(not row['errors'] for row in rows), 'invalid_count': sum(bool(row['errors']) for row in rows)}


def import_valid(db, actor, text):
    rows = inspect_import(db, actor, text)
    valid = [row for row in rows if not row['errors']]
    if not valid:
        raise HTTPException(status_code=422, detail='No valid rows to import')
    for row in valid:
        create_case(db, actor, row['_parsed'])
    db.commit()
    return {'imported': len(valid), 'skipped': len(rows) - len(valid)}
