import os
from pathlib import Path
from dotenv import load_dotenv
import sys

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / 'backend' / '.env')

USE_POSTGRES = os.getenv('USE_POSTGRES', 'False').lower() == 'true'
print('USE_POSTGRES', USE_POSTGRES)
print('DB ENV', dict(
    POSTGRES_DB=os.getenv('POSTGRES_DB'),
    POSTGRES_USER=os.getenv('POSTGRES_USER'),
    POSTGRES_PASSWORD='****' if os.getenv('POSTGRES_PASSWORD') else None,
    POSTGRES_HOST=os.getenv('POSTGRES_HOST'),
    POSTGRES_PORT=os.getenv('POSTGRES_PORT'),
))

if not USE_POSTGRES:
    print('Postgres is not enabled in .env')
    sys.exit(0)

try:
    import psycopg2
except ImportError:
    print('psycopg2 is not installed')
    sys.exit(1)

conn = psycopg2.connect(
    dbname=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('POSTGRES_HOST') or '127.0.0.1',
    port=os.getenv('POSTGRES_PORT') or 5432,
)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
print('tables:', [row[0] for row in cur.fetchall()])
cur.execute("SELECT count(*) FROM signtext_gamelevel")
print('gamelevel count:', cur.fetchone()[0])
cur.execute("SELECT id, game_key, difficulty, level_number, title FROM signtext_gamelevel ORDER BY game_key, difficulty, level_number LIMIT 20")
for row in cur.fetchall():
    print(row)
cur.execute("SELECT count(*) FROM signtext_gamelevelitem")
print('gamelevelitem count:', cur.fetchone()[0])
conn.close()
