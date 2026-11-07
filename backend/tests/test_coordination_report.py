import csv
from io import StringIO

from backend.tests.test_review2_completion import acknowledge, requested_item  # noqa: F401


def test_coordination_report_json_and_csv_exclude_completed_requests(api, requested_item):
    acknowledge(api, requested_item)
    status, report = api.request('GET', '/reports/coordination-requests')
    assert status == 200 and len(report['rows']) == 1
    row = report['rows'][0]
    assert row['aicte_id'] == 'INST-0001'
    assert row['status'] == 'acknowledged' and row['owner'] == 'Anita Rao'
    status, body, _ = api.request('GET', '/reports/coordination-requests.csv', raw=True)
    assert status == 200
    csv_row = list(csv.DictReader(StringIO(body)))[0]
    assert all(csv_row[key] == ('' if value is None else str(value)) for key, value in row.items())
    status, _ = api.request('POST', f"/coordination/{requested_item['id']}/complete", {'remarks': 'Records received'}, api.user('Anita Rao'))
    assert status == 200
    assert api.request('GET', '/reports/coordination-requests')[1]['rows'] == []
