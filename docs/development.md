# Development

## Local env

```bash
cp .env.example .env
```

For local Python without Docker set:

```bash
DB_ENGINE=sqlite
```

## Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 0.0.0.0:8050
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server: `http://localhost:5178`  
Backend API: `http://localhost:8050/api/`

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The compose file exposes backend on `127.0.0.1:8050` and frontend on
`127.0.0.1:5178`.

## First migrations

The app packages already include empty `migrations/` packages. Generate initial
migrations after dependencies are installed:

```bash
python manage.py makemigrations employees skud leave knowledge
```
