# Kumpas Backend Setup (Windows Beginner Guide)

This guide is for first-time Python users.

## 1) Install Python 3.11

Option A (quick via terminal):

```powershell
winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
```

Option B (GUI):
- Download from: https://www.python.org/downloads/windows/
- Run installer
- IMPORTANT: check **Add Python to PATH**
- Click **Install Now**

After install, close and reopen VS Code terminal.

Check:

```powershell
python --version
pip --version
```

## 2) Install PostgreSQL

Option A (winget):

```powershell
winget install -e --id PostgreSQL.PostgreSQL.17 --accept-source-agreements --accept-package-agreements
```

Option B (GUI, recommended for beginners):
- Download: https://www.postgresql.org/download/windows/
- Open installer
- Keep default port: `5432`
- Set password for user `postgres` (save this password)
- Keep pgAdmin checked
- Finish install

Check:

```powershell
psql --version
```

## 3) Prepare backend project

Open terminal in [backend/](backend/).

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) Configure environment variables

```powershell
Copy-Item .env.example .env
```

Open [.env](.env) and set values:

```env
POSTGRES_DB=kumpas_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_POSTGRES_PASSWORD
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
USE_POSTGRES=True
```

If you do not have PostgreSQL yet, you can skip `USE_POSTGRES` (or set it to `False`) and the backend will use local SQLite automatically.

## 5) Create database `kumpas_db`

Use pgAdmin (easy way):
- Open pgAdmin
- Connect using your `postgres` password
- Right click Databases -> Create -> Database
- Database name: `kumpas_db`

Or terminal:

```powershell
psql -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE kumpas_db;"
```

## 6) Run Django migrations and server

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

## 7) Open Sign-to-Text page

- Open [sign-to-text.html](..\sign-to-text.html)
- Click **Start Camera**
- Allow camera permissions

## Troubleshooting

### Python not found
- Reopen terminal first
- Run:

```powershell
$env:Path += ";$env:LocalAppData\Programs\Python\Python311;$env:LocalAppData\Programs\Python\Python311\Scripts"
python --version
```

### psql not found
- Reopen terminal
- If still missing, reinstall PostgreSQL and include command-line tools

### DB connection failed
- Check [.env](.env) password matches your PostgreSQL password
- Confirm PostgreSQL service is running in Services app
