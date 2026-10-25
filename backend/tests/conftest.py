"""Integration tests use PostgreSQL and roll back all per-test changes."""
import pytest
from sqlalchemy.orm import Session

from backend.db import engine
from backend.seed import seed_demo


@pytest.fixture
def db():
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        try:
            seed_demo(session)
            yield session
        finally:
            session.close()
            if transaction.is_active:
                transaction.rollback()


@pytest.fixture
def api():
    """Route commits release SAVEPOINTs, never the outer test transaction."""
    from backend.dependencies import get_db
    from backend.main import app
    from backend.tests.api_support import DatabaseApi

    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        previous = app.dependency_overrides.copy()

        def test_db():
            yield session

        try:
            seed_demo(session)
            session.commit()
            # Browser reviews/requests must survive verification. Isolate test
            # coordination state inside the outer transaction; rollback restores it.
            from sqlalchemy import delete
            from backend.models import CoordinationRequest, CaseLink
            session.execute(delete(CoordinationRequest))
            session.execute(delete(CaseLink))
            session.commit()
            app.dependency_overrides[get_db] = test_db
            yield DatabaseApi(session)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            session.close()
            if transaction.is_active:
                transaction.rollback()
