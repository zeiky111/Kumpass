import os, sys, json, re
from datetime import datetime

# parse .env for Postgres creds
env_path = os.path.join(os.path.dirname(__file__), '.env')
config = {}
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        config[k.strip()] = v.strip()

DB = {
    'dbname': config.get('POSTGRES_DB', 'kumpas_db'),
    'user': config.get('POSTGRES_USER', 'postgres'),
    'password': config.get('POSTGRES_PASSWORD', ''),
    'host': config.get('POSTGRES_HOST', '127.0.0.1'),
    'port': int(config.get('POSTGRES_PORT', '5432')),
}

TARGET_EMAILS = sys.argv[1:] or ['iezdtr@gmail.com']
TARGET_ID = 0

print('Connecting to Postgres', DB['host'], DB['port'], DB['dbname'])

try:
    import psycopg2
except Exception as e:
    print('psycopg2 not available:', e)
    raise

conn = psycopg2.connect(**DB)
cur = conn.cursor()

all_users = []

for TARGET_EMAIL in TARGET_EMAILS:
    cur.execute("SELECT id, username, email, first_name, last_name FROM auth_user WHERE email = %s OR username = %s OR id = %s", (TARGET_EMAIL, TARGET_EMAIL, TARGET_ID))
    users = cur.fetchall()
    if not users:
        print('No matching users found for', TARGET_EMAIL)
        continue
    print('Found users for', TARGET_EMAIL, users)
    all_users.extend(users)

if not all_users:
    print('No matching users found')
    conn.close()
    raise SystemExit(0)

# Remove duplicate users if any
seen = set()
users = []
for u in all_users:
    if u[0] in seen:
        continue
    seen.add(u[0])
    users.append(u)

timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
backup = {'users': [], 'related': {}}

for u in users:
    uid = u[0]
    backup['users'].append(dict(id=u[0], username=u[1], email=u[2], first_name=u[3], last_name=u[4]))

    # find foreign key refs to auth_user
    cur.execute("""
    SELECT
      tc.table_name, kcu.column_name
    FROM
      information_schema.table_constraints AS tc
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.constraint_schema = kcu.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND kcu.ordinal_position IS NOT NULL
      AND kcu.position_in_unique_constraint IS NOT NULL
      AND tc.constraint_schema = 'public'
      AND kcu.ordinal_position IS NOT NULL
      AND tc.table_name NOT LIKE 'pg_%'
    """)
    fks = cur.fetchall()
    # Better approach: query pg_constraint for fks referencing auth_user
    cur.execute("""
    SELECT
      conrelid::regclass::text AS table_from,
      a.attname as column_from
    FROM pg_constraint
    JOIN pg_attribute a ON a.attrelid = conrelid AND a.attnum = ANY(conkey)
    WHERE contype = 'f' AND confrelid = 'auth_user'::regclass;
    """)
    refs = cur.fetchall()
    backup['related'][str(uid)] = {}
    for table, column in refs:
        # select rows
        cur.execute(f"SELECT * FROM {table} WHERE {column} = %s", (uid,))
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        backup['related'][str(uid)][f"{table}.{column}"] = [dict(zip(colnames, r)) for r in rows]

# write backup file
bakfile = os.path.join(os.path.dirname(__file__), f'user_delete_backup_{timestamp}.json')
with open(bakfile, 'w', encoding='utf-8') as f:
    json.dump(backup, f, indent=2, default=str)
print('Backup written to', bakfile)

# Now delete related rows then user
for u in users:
    uid = u[0]
    # delete from referencing tables
    for table_column in backup['related'][str(uid)]:
        table, column = table_column.split('.')
        print('Deleting from', table, 'where', column, '=', uid)
        cur.execute(f"DELETE FROM {table} WHERE {column} = %s", (uid,))
        print('  rows deleted:', cur.rowcount)
    # also remove rows by email/username in other tables that may store them
    cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE column_name IN ('email','username') AND table_schema='public'")
    cols = cur.fetchall()
    for tname, cname in cols:
        for target_email in TARGET_EMAILS:
            try:
                cur.execute(f"DELETE FROM {tname} WHERE {cname} = %s", (target_email,))
                if cur.rowcount:
                    print('Deleted', cur.rowcount, 'rows from', tname, 'where', cname, '=', target_email)
            except Exception:
                pass
    # finally delete user
    cur.execute('DELETE FROM auth_user WHERE id = %s', (uid,))
    print('Deleted auth_user id', uid, 'rows:', cur.rowcount)

conn.commit()
conn.close()
print('Done')
