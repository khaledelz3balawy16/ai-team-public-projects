'Add restrictive foreign keys from curriculum children to curriculum.programmes.\n\nBackground\n----------\ncurriculum.programmes had NO inbound foreign keys at all. Nothing stopped a\nprogramme row being deleted while its cohorts/groups/modules still referenced\nit, which is exactly how the current orphan set was produced.\n\nStrategy (staged, non-destructive)\n----------------------------------\nThe live database ALREADY contains orphaned and empty programme_id values, so a\nplain ``ADD CONSTRAINT`` would abort the migration. This migration therefore:\n\n1. Measures the current null/empty/orphan counts for every candidate table.\n2. Adds each constraint as ``NOT VALID``.\n3. Runs ``VALIDATE CONSTRAINT`` only for tables whose data is already provably\n   clean, decided from the counts in step 1 — never by attempting a validation\n   and catching the failure.\n\n``NOT VALID`` trade-off\n-----------------------\nA ``NOT VALID`` foreign key is enforced for every INSERT and UPDATE from the\nmoment it is created, and it still blocks DELETEs of a referenced parent row.\nWhat it does NOT do is re-check the rows that already exist. That is precisely\nwhat we want here: it stops the bug from recurring immediately, without\ndeleting or mutating a single pre-existing orphan. Those orphans stay visible\nand untouched, pending a separate, CHANGE_MEly approved cleanup. Once they are\nresolved, each constraint can be promoted with:\n\n    ALTER TABLE curriculum."<table>" VALIDATE CONSTRAINT <name>;\n\nWhy ON UPDATE RESTRICT (not CASCADE)\n------------------------------------\n``programme_id`` is an identity key, not a mutable attribute. ``ON UPDATE\nCASCADE`` would grant PostgreSQL standing permission to rewrite programme_id\nacross every child table whenever a parent key changed — a silent, wide data\nmutation, and the opposite of this migration\'s purpose. ``RESTRICT`` preserves\nparent identity: re-keying a programme must be a deliberate, reviewed operation,\nnot a side effect.\n\nEmpty-string programme_id\n-------------------------\n\'\' is not NULL, so a foreign key would reject it. Rows carrying \'\' are left\nexactly as they are; their constraint simply stays NOT VALID. Converting \'\'\nto NULL is a data mutation and is deliberately NOT done here.\n\nTransaction safety\n------------------\nNothing in this migration is allowed to abort the transaction. Validation is\ngated on the measured counts, so a ``VALIDATE CONSTRAINT`` is only ever issued\nagainst a table already known to be clean. No savepoints, and no\nexception-driven control flow.\n'
from django.db import migrations


PARENT_TABLE = 'programmes'
PARENT_COLUMN = 'programme_id'

# child table -> constraint name
CHILD_TABLES = {
    'cohorts': 'cohorts_programme_id_fkey',
    'groups': 'groups_programme_id_fkey',
    'modules': 'modules_programme_id_fkey',
    'week_templates': 'week_templates_programme_id_fkey',
}

ON_DELETE = 'restrict'
ON_UPDATE = 'restrict'


def qualified(table):
    return f'curriculum."{table}"'


def table_exists(cursor, table):
    cursor.execute('select to_regclass(%s)', [f'curriculum.{table}'])
    return bool(cursor.fetchone()[0])


def column_exists(cursor, table, column):
    cursor.execute(
        '''select 1 from information_schema.columns
           where table_schema = 'curriculum' and table_name = %s and column_name = %s''',
        [table, column],
    )
    return bool(cursor.fetchone())


def constraint_exists(cursor, table, name):
    cursor.execute(
        '''select 1 from pg_constraint con
           join pg_class rel on rel.oid = con.conrelid
           join pg_namespace ns on ns.oid = rel.relnamespace
           where ns.nspname = 'curriculum' and rel.relname = %s and con.conname = %s''',
        [table, name],
    )
    return bool(cursor.fetchone())


def parent_key_is_unique(cursor):
    """The FK target must be backed by a unique or primary key constraint."""
    cursor.execute(
        '''select 1
           from pg_constraint con
           join pg_class rel on rel.oid = con.conrelid
           join pg_namespace ns on ns.oid = rel.relnamespace
           where ns.nspname = 'curriculum'
             and rel.relname = %s
             and con.contype in ('p', 'u')
             and (
               select array_agg(att.attname order by att.attname)
               from unnest(con.conkey) as k(attnum)
               join pg_attribute att
                 on att.attrelid = con.conrelid and att.attnum = k.attnum
             ) = array[%s]::name[]''',
        [PARENT_TABLE, PARENT_COLUMN],
    )
    return bool(cursor.fetchone())


def integrity_counts(cursor, table):
    """null / empty / orphan counts for one child table."""
    cursor.execute(f'''
        select
            count(*) filter (where {PARENT_COLUMN} is null) as nulls,
            count(*) filter (where {PARENT_COLUMN} = '') as empties,
            count(*) filter (
                where {PARENT_COLUMN} is not null
                  and {PARENT_COLUMN} <> ''
                  and not exists (
                      select 1 from {qualified(PARENT_TABLE)} p
                      where p.{PARENT_COLUMN} = c.{PARENT_COLUMN}
                  )
            ) as orphans
        from {qualified(table)} c
    ''')
    nulls, empties, orphans = cursor.fetchone()
    return int(nulls or 0), int(empties or 0), int(orphans or 0)


def apply_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        if not table_exists(cursor, PARENT_TABLE):
            print(f'  [skip] curriculum.{PARENT_TABLE} absent; no foreign keys added')
            return
        if not column_exists(cursor, PARENT_TABLE, PARENT_COLUMN):
            print(f'  [skip] curriculum.{PARENT_TABLE}.{PARENT_COLUMN} absent')
            return
        if not parent_key_is_unique(cursor):
            # Without this, ADD CONSTRAINT would fail anyway; failing here gives
            # a comprehensible reason instead of a raw PostgreSQL error.
            raise RuntimeError(
                f'curriculum.{PARENT_TABLE}.{PARENT_COLUMN} is not covered by a '
                'primary key or unique constraint; a foreign key cannot reference it.'
            )

        for table, constraint in CHILD_TABLES.items():
            if not table_exists(cursor, table) or not column_exists(cursor, table, PARENT_COLUMN):
                print(f'  [skip] curriculum.{table}: table or {PARENT_COLUMN} column absent')
                continue
            if constraint_exists(cursor, table, constraint):
                print(f'  [skip] curriculum.{table}: {constraint} already present')
                continue

            nulls, empties, orphans = integrity_counts(cursor, table)
            print(f'  [scan] curriculum.{table}: null={nulls} empty={empties} orphan={orphans}')

            cursor.execute(f'''
                alter table {qualified(table)}
                add constraint {constraint}
                foreign key ({PARENT_COLUMN})
                references {qualified(PARENT_TABLE)} ({PARENT_COLUMN})
                on delete {ON_DELETE}
                on update {ON_UPDATE}
                not valid
            ''')
            print(f'  [add ] curriculum.{table}: {constraint} created NOT VALID')

            # Decide from the measured counts, never by attempting VALIDATE and
            # catching the error: a failed VALIDATE aborts the transaction and
            # would take the whole migration down with it.
            if empties or orphans:
                print(
                    f'  [hold] curriculum.{table}: left NOT VALID — '
                    f'{empties} empty + {orphans} orphan row(s) need review first'
                )
                continue

            cursor.execute(
                f'alter table {qualified(table)} validate constraint {constraint}'
            )
            print(f'  [ok  ] curriculum.{table}: {constraint} VALIDATED')


def revert_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        for table, constraint in CHILD_TABLES.items():
            if table_exists(cursor, table):
                cursor.execute(
                    f'alter table {qualified(table)} drop constraint if exists {constraint}'
                )
                print(f'  [drop] curriculum.{table}: {constraint} removed if present')


class Migration(migrations.Migration):
    dependencies = [
        ('curriculum_api', '0037_free_courses_week_builder_week_ids'),
    ]

    operations = [
        migrations.RunPython(apply_schema, revert_schema),
    ]
