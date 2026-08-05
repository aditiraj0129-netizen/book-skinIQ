---
title: "Running Bright Studio in VS Code"
subtitle: "Step-by-step setup guide — backend, AI, and frontend"
---

# Running Bright Studio in VS Code

This guide walks through opening the project in VS Code and getting both the
backend (with the AI booking assistant) and the frontend running locally.

There are two parts to run: **the backend** (FastAPI + Postgres + the Grok/RAG
AI agent) and **the frontend** (React). You'll run them in two separate VS
Code terminals, side by side.

---

## 0. Prerequisites

Install these once, if you don't already have them:

- **VS Code**: <https://code.visualstudio.com>
- **Python 3.11+**: <https://www.python.org/downloads>
- **Node.js 20+**: <https://nodejs.org>
- **PostgreSQL** running locally (or use the provided `docker-compose.yml` if
  you have Docker installed — see the last section of this guide)
- **Git** (to clone/manage the repo)

Recommended VS Code extensions (VS Code will usually prompt you to install
these automatically when you open the project):

- **Python** (`ms-python.python`)
- **Pylance** (`ms-python.vscode-pylance`)
- **ES7+ React/Redux/JS snippets** (optional, for the frontend)
- **Tailwind CSS IntelliSense** (optional, nice-to-have for the frontend)

---

## 1. Open the project

1. Unzip / place the `appointment-ai` folder wherever you keep projects.
2. Open VS Code.
3. **File → Open Folder…** and select the `appointment-ai` folder (the one
   containing `backend/`, `frontend/`, and `docker-compose.yml`).
4. Open the integrated terminal: **Terminal → New Terminal**, or `` Ctrl+` ``
   (backtick).

---

## 2. Backend setup (the AI part)

All commands below run in the VS Code terminal, from the project root.

### 2.1 Create a virtual environment

```bash
cd backend
python3 -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Your terminal prompt should now show `(.venv)` at the start of the line.

### 2.2 Point VS Code at this environment

1. Press `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac) to open the Command Palette.
2. Type **"Python: Select Interpreter"** and choose the one at
   `backend/.venv/bin/python` (or `backend\.venv\Scripts\python.exe` on
   Windows).

This makes Pylance's autocomplete, linting, and the built-in test runner all
use the same environment as your terminal.

### 2.3 Install dependencies

```bash
pip install -r requirements.txt
```

This takes a minute or two — it installs FastAPI, SQLAlchemy, LangChain, the
Grok (xAI) client, FAISS, and everything else the AI layer needs.

### 2.4 Configure environment variables

```bash
cp .env.example .env
```

Open the new `backend/.env` file in VS Code and fill in what you have:

```ini
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/appointments

JWT_SECRET=pick-any-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=pick-a-password

# Leave blank to run on the built-in rule-based fallback instead of Grok
XAI_API_KEY=your-grok-api-key-here
XAI_MODEL=grok-4

# Leave blank to use the free local embeddings for the knowledge-base search
OPENAI_API_KEY=
```

**You do not need `XAI_API_KEY` to run the app.** Leave it blank and the
assistant runs on a deterministic rule-based booking flow instead — useful
for testing everything else first.

### 2.5 Make sure Postgres is running

If you have Postgres installed locally, create the database once:

```bash
createdb appointments
```

(If that command isn't found, open `psql` and run `CREATE DATABASE appointments;`)

If you'd rather not install Postgres locally, skip to **Section 5** and use
Docker Compose instead — it starts Postgres for you automatically.

### 2.6 Seed the database and build the AI knowledge index

```bash
python -m app.seed
python -m app.build_rag_index
```

You should see output confirming an admin user, four services, and the
knowledge-base index were created.

### 2.7 Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Leave this terminal running. Open **`http://localhost:8000/docs`** in your
browser — this is FastAPI's interactive API explorer. Try
`POST /api/chat` with `{"message": "I want to book a haircut"}` to confirm
the AI assistant responds.

> **Using the VS Code Debugger instead:** the project ships a
> `.vscode/launch.json`. Open the **Run and Debug** panel (`Ctrl+Shift+D`)
> and pick **"FastAPI: uvicorn (reload)"**, then press the green ▶ button.
> This lets you set breakpoints directly in the AI agent code.

### 2.8 Run the backend tests (optional but recommended)

In the same terminal:

```bash
pytest tests/ -v
```

All 27 tests should pass — these cover the scheduling engine, conflict
detection, the RAG retrieval pipeline, and the fallback NLU.

---

## 3. Frontend setup

Open a **second terminal** in VS Code (click the `+` icon in the terminal
panel, or `` Ctrl+Shift+` ``) so the backend keeps running in the first one.

```bash
cd frontend
npm install
cp .env.example .env
```

Open `frontend/.env` and confirm it points at your backend:

```ini
VITE_API_URL=http://localhost:8000
```

Then start the dev server:

```bash
npm run dev
```

Open **`http://localhost:5173`** in your browser. You should see the Bright
Studio landing page, with a floating **"Ask Aria"** button bottom-right.

---

## 4. Trying it out

- **As a customer**: click "Ask Aria" (or click any service card) and try
  something like *"I'd like to book a massage next Monday at 2pm"*. Watch
  the header badge — it says **"Rule-based mode"** if `XAI_API_KEY` is
  blank, or **"Powered by Grok"** if it's set.
- **As staff**: click **"Staff login"** top-right, sign in with the
  `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your `.env` (defaults:
  `admin` / `admin123` if you didn't seed with something else), and you'll
  land on the admin dashboard with live stats, charts, and appointment
  management.

---

## 5. Alternative: running everything with Docker (optional)

If you have Docker Desktop installed, you can skip steps 2.5–2.7 and 3
entirely:

```bash
# from the project root
docker compose up --build
```

This starts Postgres (with the pgvector extension pre-installed), seeds the
database, builds the AI knowledge index, and starts both the backend
(`:8000`) and frontend (`:5173`) automatically. Set `XAI_API_KEY` in a `.env`
file at the project root first if you want live Grok responses:

```ini
XAI_API_KEY=your-grok-api-key-here
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` when running Python commands | You likely forgot to activate the venv (`source .venv/bin/activate`) or select it as the VS Code interpreter. |
| `psycopg2` / database connection errors | Confirm Postgres is running and `DATABASE_URL` in `backend/.env` matches your local credentials. |
| Frontend loads but shows "Loading services…" forever | The backend isn't running, or `VITE_API_URL` in `frontend/.env` doesn't match the port `uvicorn` is running on. |
| Chat always says "Rule-based mode" even with a key set | Double-check `XAI_API_KEY` is in `backend/.env` (not `frontend/.env`) and restart `uvicorn` — env vars are only read at startup. |
| Port `8000` or `5173` already in use | Stop whatever else is using it, or run with a different port: `uvicorn app.main:app --reload --port 8001` (and update `VITE_API_URL` to match). |

---

*Generated as part of the Bright Studio appointment booking assistant
project setup.*
