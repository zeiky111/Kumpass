# Kumpas Django Backend (Sign-to-Text)

## 1) Create virtual environment

```bash
python -m venv .venv
.venv\\Scripts\\activate
```

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Configure environment

- Copy `.env.example` to `.env`
- Update PostgreSQL values if needed

## 4) Create PostgreSQL database

Create a database named `kumpas_db` (or your custom name from `.env`).

## 5) Run migrations

```bash
python manage.py migrate
```

## 6) Start server

```bash
python manage.py runserver 127.0.0.1:8000
```

## 7) API quick test

- Health: `GET http://127.0.0.1:8000/api/health/`
- Predict: `POST http://127.0.0.1:8000/api/sign/predict/`
- Recent logs: `GET http://127.0.0.1:8000/api/sign/recent/`

## No-Training AI Mode (Fastest for Demo)

If you need broader word translation without collecting custom training data:

1. Create a free key at OpenRouter
2. Set in `.env`:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=qwen/qwen2.5-vl-72b-instruct:free
```

3. Restart Django server

When enabled, `/api/sign/predict/` tries AI vision translation first, then falls back to local heuristics if unavailable.

## Camera API selected

This setup uses browser WebRTC via `navigator.mediaDevices.getUserMedia` on the frontend. Captured frames are sent to Django as base64 images for prediction.

## Next model step

Replace `signtext/inference.py` with your real ML model (for example TensorFlow, MediaPipe, or a custom PyTorch classifier).

## Train SVC for Finger Spelling

1. Open `collect-landmarks.html` in browser and collect rows for labels A,B,D,F,I,L,W,Y.
2. Download CSV and move it to `backend/training/landmarks.csv`.
3. Train model:

```bash
python training/train_svc_from_csv.py --csv training/landmarks.csv --out models/fingerspelling_svc.joblib
```

4. Restart Django server. The API auto-loads the trained model from `models/fingerspelling_svc.joblib`.
