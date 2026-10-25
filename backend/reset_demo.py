"""Explicit local demo reset. Never called by seeding or routine verification."""
import os

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.analytics import dashboard_summary
from backend.db import engine
from backend.migrate_raw_region import apply_migration
from backend.seed import ROOT, read_rows, seed_demo

TABLES = ('action_log', 'coordination_requests', 'case_links', 'cases', 'users', 'institutions')


def reset_demo(connection):
    """Recreate the six demo tables atomically, also usable in rollback tests.

    The caller owns the outer transaction. No CASCADE, schema deletion or
    volume deletion is used. Unknown public tables cause refusal before DDL.
    """
    with connection.begin_nested():
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(text("SET LOCAL search_path TO public"))
        connection.execute(text('SELECT pg_advisory_xact_lock(2626401)'))
        existing = set(inspect(connection).get_table_names(schema='public'))
        if existing not in (set(), set(TABLES)):
            raise RuntimeError('Expected only the six CaseBridge tables (or an empty public schema); reset refused.')
        # Fixed identifiers only. Foreign keys between these tables are removed
        # together; external dependencies fail instead of cascading to other data.
        names = ', '.join('public.' + name for name in TABLES)
        connection.execute(text('DROP TABLE IF EXISTS ' + names))
        schema = (ROOT / 'schema.sql').read_text(encoding='utf-8-sig')
        for statement in schema.split(';'):
            if statement.strip():
                connection.execute(text(statement))
        apply_migration(connection, read_rows('seed_cases.csv'))
        with Session(bind=connection, join_transaction_mode='create_savepoint') as db, db.begin():
            seed_demo(db)
            summary = dashboard_summary(db)
        return summary


def main():
    url = make_url(os.environ['DATABASE_URL'])
    if url.host not in ('localhost', '127.0.0.1', '::1') or url.database != os.environ.get('POSTGRES_DB'):
        raise RuntimeError('Reset is restricted to the local demo database named by POSTGRES_DB.')
    with engine.begin() as connection:
        summary = reset_demo(connection)
    print('PASS: Demo reset committed (six tables, approved raw_region migration, seed loaded).')
    print('Cases: {total}; pending: {pending}; under_process: {under_process}; '
          'escalated: {escalated}; transferred: {transferred}; disposed: {disposed}; open: {open}'.format(**summary))
    print('Previous demo actions, links and coordination requests have been removed.')


if __name__ == '__main__':
    main()
