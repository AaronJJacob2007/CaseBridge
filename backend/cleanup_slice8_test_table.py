"""Remove only the empty table leaked by the initial Slice 8 refusal test."""
import os

from sqlalchemy import Integer, inspect, insert, text
from sqlalchemy.engine import make_url

from backend.db import engine
from backend.models import ActionLog

TARGET = 'slice8_unexpected_table'


def cleanup(connection):
    if TARGET not in inspect(connection).get_table_names(schema='public'):
        return 'Test table already absent; no changes made.'
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text('LOCK TABLE public.slice8_unexpected_table IN ACCESS EXCLUSIVE MODE'))
    inspector = inspect(connection)
    columns = inspector.get_columns(TARGET, schema='public')
    if (len(columns) != 1 or columns[0]['name'] != 'id'
            or not isinstance(columns[0]['type'], Integer)
            or not columns[0]['nullable'] or columns[0].get('default') is not None
            or columns[0].get('identity') or columns[0].get('computed')
            or inspector.get_pk_constraint(TARGET, schema='public')['constrained_columns']
            or inspector.get_foreign_keys(TARGET, schema='public')
            or inspector.get_unique_constraints(TARGET, schema='public')
            or inspector.get_check_constraints(TARGET, schema='public')
            or inspector.get_indexes(TARGET, schema='public')):
        raise RuntimeError('Test table structure differs; cleanup refused.')
    if connection.scalar(text('SELECT count(*) FROM public.slice8_unexpected_table')) != 0:
        raise RuntimeError('Test table contains records; cleanup refused.')
    # No CASCADE: any external dependent object blocks this targeted cleanup.
    connection.execute(text('DROP TABLE public.slice8_unexpected_table'))
    connection.execute(insert(ActionLog).values(
        event_type='update', remarks='Remove empty slice8_unexpected_table left by the initial Slice 8 test; demo records preserved.',
    ))
    return 'PASS: Empty Slice 8 test table removed; demo records preserved.'


if __name__ == '__main__':
    url = make_url(os.environ['DATABASE_URL'])
    if url.host not in ('localhost', '127.0.0.1', '::1') or url.database != os.environ.get('POSTGRES_DB'):
        raise RuntimeError('Cleanup is restricted to the local demo database named by POSTGRES_DB.')
    with engine.begin() as connection:
        result = cleanup(connection)
    print(result)
