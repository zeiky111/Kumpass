import sqlite3, shutil, datetime, os

TARGET_ID = 16

here = os.path.dirname(__file__)
db_path = os.path.join(here, 'db.sqlite3')
if not os.path.exists(db_path):
    print('Database not found:', db_path)
    raise SystemExit(2)

bak = db_path + '.bak.manual.' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
shutil.copy(db_path, bak)
print('Backup created at', bak)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]

total_deleted = 0
for t in tables:
    try:
        cur.execute(f"PRAGMA table_info('{t}')")
        cols = [r[1] for r in cur.fetchall()]
        deleted = 0
        if 'user_id' in cols:
            cur.execute(f"DELETE FROM '{t}' WHERE user_id=?", (TARGET_ID,))
            deleted = cur.rowcount
        # try username/email columns too
        if 'email' in cols:
            cur.execute(f"DELETE FROM '{t}' WHERE email=?", ('iezdtr@gmail.com',))
            deleted += cur.rowcount
        if 'username' in cols:
            cur.execute(f"DELETE FROM '{t}' WHERE username=?", ('iezdtr@gmail.com',))
            deleted += cur.rowcount
        if deleted:
            print(f"Deleted {deleted} rows from {t}")
            total_deleted += deleted
    except Exception as e:
        # ignore errors for complex tables
        pass

# Finally delete from auth_user by id
cur.execute('DELETE FROM auth_user WHERE id=?', (TARGET_ID,))
print('Deleted from auth_user rows:', cur.rowcount)

conn.commit()
conn.close()
print('Total rows deleted (approx):', total_deleted)
print('Done')
