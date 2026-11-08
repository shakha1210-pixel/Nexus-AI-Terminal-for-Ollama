# NEXUS AI — Foundation 0.1.0

NEXUS AI is a local-first AI workspace. This first milestone provides a React dashboard, a FastAPI gateway, and live connection/model discovery from Ollama.

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.10+
- Node.js 20+
- Ollama installed and running

## 1. Start Ollama

Install Ollama from https://ollama.com and start it. In a terminal, you can download a starter model:

```powershell
ollama pull llama3.2
```

Ollama's local API should respond at `http://127.0.0.1:11434`.

## 2. Start the backend (PowerShell)

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again.

Backend health: http://127.0.0.1:8000/api/health

API docs: http://127.0.0.1:8000/docs

## 3. Start the frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally http://127.0.0.1:5173).

## Configuration

Backend settings are in `backend/.env`:

- `OLLAMA_BASE_URL`: Ollama API address (default `http://127.0.0.1:11434`)
- `FRONTEND_ORIGINS`: comma-separated browser origins allowed by CORS
- `REQUEST_TIMEOUT_SECONDS`: Ollama request timeout

Frontend API address can be overridden by creating `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Current scope

- Dark and light themes
- Responsive left navigation and dashboard shell
- Ollama connectivity status
- Installed model listing and basic metadata
- FastAPI health endpoint

Navigation items beyond Dashboard are visual placeholders in this milestone. Model pulling, chat streaming, agents, workflows, persistence, and Tauri desktop packaging will be added in subsequent milestones.

## Project layout

```text
backend/   FastAPI API and Ollama service
frontend/  React + TypeScript dashboard
```

The standalone `nexus-ai/` folder is an earlier UI prototype; use the root
`backend/` and `frontend/` directories for the integrated application described
above.
