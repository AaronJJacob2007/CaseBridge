"""Reset tests recreate tables only inside rollback transactions.

No test permanently resets the user's demo or changes its expectations.
"""
import pytest
from sqlalchemy import inspect, insert, select, text

from backend.db import engine
from backend.models import Base, Case, CaseLink, CoordinationRequest, User
from backend.reset_demo import reset_demo
import backend.reset_demo as reset_module


def snapshot(connection):
    return {name: list(connection.execute(table.select().order_by(table.c.id)))
            for name, table in Base.metadata.tables.items()}


def test_reset_restores_reference_and_rollback_preserves_live_records():
    with engine.connect() as connection:
        before = snapshot(connection)
        connection.rollback()
        transaction = connection.begin()
        try:
            # Simulate the status drift that previously caused nine failures.
            connection.execute(text("UPDATE public.cases SET status='disposed' WHERE case_code='PGRC-111'"))
            pair = sorted(connection.execute(select(Case.id).where(Case.case_code.in_(['PGRC-101', 'RB-201']))).scalars())
            link_id = connection.execute(select(CaseLink.id).where(CaseLink.case_a == pair[0], CaseLink.case_b == pair[1])).scalar_one_or_none()
            if link_id is None:
                link_id = connection.execute(insert(CaseLink).values(case_a=pair[0], case_b=pair[1], type='cross_bureau_overlap', review_state='confirmed').returning(CaseLink.id)).scalar_one()
            institution_id = connection.execute(select(Case.institution_id).where(Case.id == pair[0])).scalar_one()
            officer_id = connection.execute(select(User.id).where(User.name == 'Rahul Mehta')).scalar_one()
            connection.execute(insert(CoordinationRequest).values(link_id=link_id, institution_id=institution_id, requested_by=officer_id, to_bureau='PGRC', action_type='Slice 8 reset sentinel', status='requested'))
            summary = reset_demo(connection)
            for key, expected in {'total': 30, 'pending': 10, 'under_process': 12,
                                  'escalated': 2, 'transferred': 1, 'disposed': 5,
                                  'open': 25, 'overdue': 7, 'due_within_7_days': 7}.items():
                assert summary[key] == expected
            assert set(inspect(connection).get_table_names(schema='public')) == set(Base.metadata.tables)
            assert next(row for row in inspect(connection).get_columns('cases') if row['name'] == 'raw_region')['nullable']
            assert connection.execute(select(Case.status).where(Case.case_code == 'PGRC-111')).scalar_one() == 'pending'
            assert connection.execute(select(CaseLink.id)).all() == []
            assert connection.execute(select(CoordinationRequest.id)).all() == []
            assert len(connection.execute(select(User.id)).all()) == 6
            assert {row['region']: row['total'] for row in summary['region_wise']} == {'Central': 5, 'East': 6, 'North': 2, 'South': 5, 'West': 12}
            assert reset_demo(connection) == summary
        finally:
            transaction.rollback()
        assert snapshot(connection) == before


def test_reset_failure_after_ddl_restores_all_records(monkeypatch):
    def fail_seed(db):
        raise RuntimeError('Constructed seed failure')

    with engine.connect() as connection:
        before = snapshot(connection)
        connection.rollback()
        transaction = connection.begin()
        try:
            monkeypatch.setattr(reset_module, 'seed_demo', fail_seed)
            with pytest.raises(RuntimeError, match='Constructed seed failure'):
                reset_demo(connection)
            assert snapshot(connection) == before
        finally:
            transaction.rollback()
        assert snapshot(connection) == before


def test_reset_refuses_unexpected_tables_without_changing_records():
    with engine.connect() as connection:
        before = snapshot(connection)
        connection.rollback()
        transaction = connection.begin()
        try:
            connection.execute(text('CREATE TABLE public.slice8_unexpected_table (id integer)'))
            with pytest.raises(RuntimeError, match='reset refused'):
                reset_demo(connection)
            assert snapshot(connection) == before
            assert 'slice8_unexpected_table' in inspect(connection).get_table_names(schema='public')
        finally:
            # begin() as a context manager commits on success. Always roll back
            # this outer test transaction, even when reset correctly refuses.
            transaction.rollback()
        assert 'slice8_unexpected_table' not in inspect(connection).get_table_names(schema='public')
        assert snapshot(connection) == before
