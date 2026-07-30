import sqlite3, glob, os

db_dir = os.path.dirname(__file__)
patterns = ['db.sqlite3', 'db.sqlite3.bak*', 'db.sqlite3.precleanup.bak']
found = False
for p in patterns:
    for path in glob.glob(os.path.join(db_dir, p)):
        try:
            print('Checking', path)
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT id, username, email, first_name, last_name FROM auth_user WHERE email LIKE '%' || ? || '%' OR username LIKE '%' || ? || '%' LIMIT 50", ('iezdtr', 'iezdtr'))
            rows = cur.fetchall()
            print('Found', len(rows), 'rows in', path)
            for r in rows:
                print(r)
            conn.close()
            if rows:
                found = True
        except Exception as e:
            print('Could not open', path, 'as sqlite:', e)

if not found:
    print('No matches found in any db files')
