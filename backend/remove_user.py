import sqlite3, shutil, datetime, sys, os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
if not os.path.exists(db_path):
    print('Database not found:', db_path)
    sys.exit(2)

bak = db_path + '.bak.manual.' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
shutil.copy(db_path, bak)
print('Backup created at', bak)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
email = 'iezdtr@gmail.com'
cur.execute("SELECT id, username, email FROM auth_user WHERE email=? OR username=?", (email, email))
rows = cur.fetchall()
if not rows:
    print('No matching user found for', email)
    conn.close()
    sys.exit(0)

for (uid, username, user_email) in rows:
    print('Found user id=', uid, 'username=', username, 'email=', user_email)
    # Find tables with user_id column and delete referencing rows
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        try:
            cur.execute(f"PRAGMA table_info('{t}')")
            cols = [r[1] for r in cur.fetchall()]
            if 'user_id' in cols:
                cur.execute(f"DELETE FROM '{t}' WHERE user_id=?", (uid,))
                print('Deleted', cur.rowcount, 'rows from', t)
        except Exception as e:
            # ignore tables we can't touch
            pass
    # Also try tables that reference user by email/username
    for col in ('email','username'):
        for t in tables:
            try:
                cur.execute(f"PRAGMA table_info('{t}')")
                cols = [r[1] for r in cur.fetchall()]
                if col in cols:
                    cur.execute(f"DELETE FROM '{t}' WHERE {col}=?", (email,))
                    if cur.rowcount:
                        print('Deleted', cur.rowcount, 'rows from', t, 'by', col)
            except Exception:
                pass
    cur.execute("DELETE FROM auth_user WHERE id=?", (uid,))
    print('Deleted user from auth_user, rows affected=', cur.rowcount)

conn.commit()
conn.close()
print('Done')
