"""Slice 5 user discovery is read-only and uses real PostgreSQL identities."""
import pytest
from sqlalchemy import func, select

from backend.models import ActionLog, User


def test_demo_catalog_contains_actual_database_profiles(api):
    status, users = api.request("GET", "/demo/users")
    assert status == 200 and len(users) == 6
    expected = [{key: getattr(user, key) for key in ("id", "name", "role", "bureau", "region")}
                for user in api.db.scalars(select(User).order_by(User.id))]
    assert users == expected


@pytest.mark.parametrize("name", ["Anita Rao", "Dr. R. K. Sharma"])
def test_selected_demo_user_comes_from_header(api, name):
    actor_id = api.user(name)
    status, user = api.request("GET", "/demo/me", user=actor_id)
    assert status == 200 and user["id"] == actor_id and user["name"] == name
    expected_role = "supervisor" if name == "Dr. R. K. Sharma" else "officer"
    assert user["role"] == expected_role


@pytest.mark.parametrize("header", [None, "not-an-id", "2147483647"])
def test_missing_or_invalid_identity_read_is_403_without_a_write_audit(api, header):
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    status, result = api.request("GET", "/demo/me", user=header)
    assert status == 403 and result["detail"] == "Select a valid demo user"
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before


def test_successful_demo_reads_do_not_add_audit_rows(api):
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    assert api.request("GET", "/demo/users")[0] == 200
    assert api.request("GET", "/demo/me", user=api.user("Anita Rao"))[0] == 200
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before
