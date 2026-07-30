import sqlite3
import sys

DB='backend/db.sqlite3'
try:
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables=cur.fetchall()
    print('Tables:', tables)
    try:
        cur.execute("SELECT id, username, email, is_active, date_joined FROM auth_user ORDER BY id LIMIT 200")
        rows=cur.fetchall()
        print('auth_user rows:')
        for r in rows:
            print(r)
    except Exception as e:
        print('Could not read auth_user:', e)
    con.close()
except Exception as e:
    print('DB open error:', e)
    sys.exit(1)
