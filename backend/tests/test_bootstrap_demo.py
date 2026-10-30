import pytest
from sqlalchemy import func, select

from backend.bootstrap_demo import bootstrap
from backend.models import Case, CoordinationRequest


def test_bootstrap_rerun_preserves_existing_work(db):
    before = (
        db.scalar(select(func.count()).select_from(Case)),
        db.scalar(select(func.count()).select_from(CoordinationRequest)),
    )
    created, inserted = bootstrap(db.connection())
    assert (created, inserted) == (False, 0)
    assert before == (
        db.scalar(select(func.count()).select_from(Case)),
        db.scalar(select(func.count()).select_from(CoordinationRequest)),
    )


def test_bootstrap_refuses_partial_schema(db, monkeypatch):
    class PartialSchema:
        def get_table_names(self, schema):
            return ["cases"]

    monkeypatch.setattr("backend.bootstrap_demo.inspect", lambda connection: PartialSchema())
    with pytest.raises(RuntimeError, match="partial schema"):
        bootstrap(db.connection())
