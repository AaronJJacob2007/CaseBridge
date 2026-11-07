from sqlalchemy import func, select
from backend.models import Case, ActionLog


def test_import_preview_and_confirmation_preserve_unresolved_identity(api):
    officer = api.user('Anita Rao')
    csv = ('case_code,institution_name,aicte_id,received_on\n'
           'IMPORT-1,Example College,INST-0001,2026-10-01\n'
           'IMPORT-2,Unknown College,NO-SUCH-ID,2026-10-02\n'
           'PGRC-101,Duplicate,INST-0001,2026-10-01\n'
           'IMPORT-3,Bad date,INST-0001,not-a-date\n')
    before = api.db.scalar(select(func.count()).select_from(Case))
    status, preview = api.request('POST', '/cases/import/preview', {'csv_text': csv}, officer)
    assert status == 200 and (preview['valid_count'], preview['invalid_count']) == (2, 2)
    assert preview['rows'][1]['warnings'] and preview['rows'][2]['errors'] and preview['rows'][3]['errors']
    assert api.db.scalar(select(func.count()).select_from(Case)) == before
    status, result = api.request('POST', '/cases/import', {'csv_text': csv}, officer)
    assert status == 200 and result == {'imported': 2, 'skipped': 2}
    known = api.db.scalar(select(Case).where(Case.case_code == 'IMPORT-1'))
    unknown = api.db.scalar(select(Case).where(Case.case_code == 'IMPORT-2'))
    assert known.identity_resolved and known.bureau == 'PGRC' and known.officer_id == officer
    assert not unknown.identity_resolved and unknown.institution_id is None
    assert api.db.scalar(select(func.count()).select_from(ActionLog).where(ActionLog.case_id == known.id)) == 1
    status, second = api.request('POST', '/cases/import/preview', {'csv_text': csv}, officer)
    assert status == 200 and second['valid_count'] == 0


def test_import_rejects_supervisors_bad_headers_and_cross_bureau_fields(api):
    supervisor = api.user('Dr. R. K. Sharma')
    officer = api.user('Anita Rao')
    csv = 'case_code,institution_name\nIMPORT-4,Example\n'
    assert api.request('POST', '/cases/import/preview', {'csv_text': csv}, supervisor)[0] == 403
    assert api.request('POST', '/cases/import', {'csv_text': csv}, supervisor)[0] == 403
    assert api.request('POST', '/cases/import/preview', {'csv_text': 'case_code,bureau\nX,RB\n'}, officer)[0] == 422
    assert api.request('POST', '/cases/import/preview', {'csv_text': 'case_code,institution_name,case_code\nX,A,X\n'}, officer)[0] == 422
