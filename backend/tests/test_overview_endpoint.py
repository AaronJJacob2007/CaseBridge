def test_overview_matches_existing_endpoints(api):
    status, overview = api.request("GET", "/dashboard/overview")
    assert status == 200
    for key, path in (("summary", "/dashboard/summary"), ("alerts", "/alerts"), ("cases", "/cases")):
        status, expected = api.request("GET", path)
        assert status == 200
        assert overview[key] == expected
