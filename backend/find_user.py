import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
search_terms = ['iezdtr@gmail.com', 'iezdtr', 'Carl', 'Santos']
query = "SELECT id, username, email, first_name, last_name FROM auth_user WHERE "
conds = []
params = []
for t in search_terms:
    conds.append("email LIKE ?")
    params.append(f"%{t}%")
    conds.append("username LIKE ?")
    params.append(f"%{t}%")
    conds.append("first_name LIKE ?")
    params.append(f"%{t}%")
    conds.append("last_name LIKE ?")
    params.append(f"%{t}%")
query += " OR ".join(conds) + " LIMIT 50"
cur.execute(query, params)
rows = cur.fetchall()
print('Found', len(rows), 'rows')
for r in rows:
    print(r)
conn.close()
