import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

def safe_fetch(q):
    try:
        cur.execute(q)
        return cur.fetchall()
    except Exception as e:
        return str(e)

print('auth_user count:', safe_fetch("SELECT COUNT(*) FROM auth_user"))
print('auth_user sample:', safe_fetch("SELECT id, username, email, is_active FROM auth_user ORDER BY id DESC LIMIT 20"))
print('userprofile count:', safe_fetch("SELECT COUNT(*) FROM signtext_userprofile"))
print('userprofile sample:', safe_fetch("SELECT id, user_id, full_name, role, active FROM signtext_userprofile ORDER BY id DESC LIMIT 20"))
conn.close()
