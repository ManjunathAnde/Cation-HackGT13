# Cation

HackGT 13, Impiricus challenge. An agent that sends doctors research cards over RCS,
learns from their Yes / Not interested replies, and feeds the learned profile to a
simulated Impiricus ION platform. See `CLAUDE.md` for details.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Setup (once)

Copy the env template into the backend and fill in keys as needed:

```bash
cp .env.example backend/.env
```

## Run the backend (http://localhost:8000)

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS/Linux:           source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check it: http://localhost:8000/health should return `{"ok": true}`.

## Run the frontend (http://localhost:5173)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. It shows **backend connected ✓** if the backend is up,
or **backend not running** if it isn't.
