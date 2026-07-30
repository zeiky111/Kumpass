import sqlite3
import os

os.chdir(os.path.dirname(__file__))
for db in ["backend/db.sqlite3", "db.sqlite3"]:
    if os.path.exists(db):
        print('DB', db)
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        try:
            cur.execute('PRAGMA table_info(signtext_gamelevel)')
            print('gamelevel schema:', cur.fetchall())
            cur.execute('SELECT id, game_key, difficulty, level_number, title, is_published, created_at, updated_at FROM signtext_gamelevel LIMIT 20')
            rows = cur.fetchall()
            print('gamelevels count', len(rows))
            for r in rows:
                print(r)
            cur.execute('SELECT id, level_id, prompt, answer, media_url, extra_data FROM signtext_gamelevelitem LIMIT 20')
            rows = cur.fetchall()
            print('items count', len(rows))
            for r in rows:
                print(r)
        except Exception as e:
            print('err', e)
        conn.close()
    else:
        print('missing db', db)
