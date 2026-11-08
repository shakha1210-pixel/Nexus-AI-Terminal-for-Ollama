# NEXUS AI — English

NEXUS AI is a local-first dashboard for checking the Ollama runtime and viewing
models installed on your machine. A FastAPI backend acts as the browser-facing
gateway to Ollama.

> **Current status:** The local dashboard, backend health/status endpoints,
> Ollama model discovery, and optional Kaggle GPU controls are implemented.
> Kaggle requires the operator to configure account credentials and notebook
> secrets. Chat, agent execution, UI model downloads, and workflows are not
> implemented.

The project is distributed under the [MIT License](LICENSE).

## Requirements

- Windows 10/11, macOS, or Linux
- Python 3.10 or later
- Node.js 20 or later (npm included)
- Ollama installed and running for local model status

## Local setup

### 1. Start Ollama

Install Ollama from <https://ollama.com>. Start the Ollama application; if it is
not already running, start `ollama serve` in a separate terminal. Download a
model:

```powershell
ollama pull llama3.2
ollama list
```

The default Ollama API address is `http://127.0.0.1:11434`.

### 2. Start the backend

Open PowerShell at the repository root:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Create `.env` only once. If it already exists, keep it and edit the existing
file rather than overwriting local credentials.

If PowerShell blocks virtual-environment activation, run the following in that
PowerShell process, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The backend runs at <http://127.0.0.1:8000>. Interactive API documentation is
available at <http://127.0.0.1:8000/docs>.

### 3. Start the frontend

Open a second PowerShell window at the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173/>.

The frontend defaults to the API at `http://127.0.0.1:8000`. To change it, create
`frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart Vite after changing frontend environment variables.

## Configuration

Backend settings are read from `backend/.env`:

| Variable | Purpose | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama HTTP API | `http://127.0.0.1:11434` |
| `FRONTEND_ORIGINS` | Comma-separated CORS origins | Vite localhost origins |
| `REQUEST_TIMEOUT_SECONDS` | Ollama HTTP timeout | `8` |
| `KAGGLE_USERNAME` | Kaggle account username | Empty |
| `KAGGLE_KEY` | Kaggle API token | Empty |
| `KAGGLE_KERNEL_NAME` | Private Kaggle kernel name | `nexus-ollama-server` |
| `NGROK_DOMAIN` | Reserved ngrok domain without `https://` | Empty |
| `TUNNEL_USER` | Basic-auth username for the tunnel | `nexus` |
| `TUNNEL_PASSWORD` | Strong tunnel password | Empty |

The Kaggle notebook also requires `NGROK_TOKEN` and `TUNNEL_PASSWORD` in Kaggle
Notebook Secrets. The backend tunnel password and Kaggle Secret must match.
Never commit `.env` files, API keys, ngrok tokens, or tunnel passwords.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check that the backend is responding |
| `GET` | `/api/ollama/status` | Check the selected Ollama runtime |
| `GET` | `/api/ollama/models` | List models from the selected Ollama runtime |
| `GET` | `/api/kaggle/status` | Read Kaggle launch and connection state |
| `POST` | `/api/kaggle/start` | Start Kaggle runtime; JSON body: `{"model":"llama3.2"}` |
| `POST` | `/api/kaggle/mode` | Select `local` or ready `kaggle` runtime |

## Build and verification

From `frontend/`:

```powershell
npm run build
```

From `backend/` with its virtual environment activated:

```powershell
python -m compileall -q app
```

Quick local checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/ollama/status
Invoke-RestMethod http://127.0.0.1:8000/api/ollama/models
```

See [terminal commands and workflows](terminal%20commands.md) for the full
copy-ready guide and diagrams.

## Repository layout

```text
backend/   FastAPI API, Ollama/Kaggle services, schemas, notebook template
frontend/  React + TypeScript dashboard
nexus-ai/  Earlier standalone UI prototype (not the integrated application)
```


## Windows desktop launcher (Stage 2)

Install the backend and optional desktop dependencies:

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install -r desktop/requirements.txt
```

After building the frontend, run from the repository root:

```powershell
python desktop/launcher.py
```

- `--browser` opens the system browser instead of PyWebView.
- `--dev` also starts the Vite development server on port 5173.
- `--port 8123` changes the FastAPI port (default: 8000).
- On Windows, if the WebView2 Runtime is not detected, the launcher explains how to install the official runtime and falls back to the browser.
- Ollama remains a separate installation; the launcher does not bundle or start it.
- The tray menu can reopen the window or exit the application. If optional PyWebView/tray packages are unavailable, browser fallback is used.
- A Windows named mutex prevents a second NEXUS instance from starting.

PyWebView, tray, and WebView2 behavior still needs validation on a real Windows 10/11 machine; Linux CI cannot fully verify those platform integrations.


### Windows preflight and application icon

On a Windows 10/11 machine, run:

```powershell
python -m pip install -r desktop/requirements.txt
python scripts/create_icon.py
powershell -ExecutionPolicy Bypass -File scripts/windows-smoke-test.ps1
python desktop/launcher.py
```

`create_icon.py` generates the multi-size `desktop/assets/icon.ico` file. The preflight script checks Python, the frontend build, WebView2 Runtime files, and the icon; it does not install anything or launch the app. Final WebView2, window close/minimize, tray, and reopen behavior still require manual testing on a real Windows machine.


### Settings and credentials (Stage 3)

- Theme, sound, and UI language are stored in the per-user data directory: `%LOCALAPPDATA%\\NEXUS AI` on Windows.
- Existing `backend/.nexus` settings are copied to the new location on first launch; legacy files are not deleted.
- Kaggle, tunnel, and OpenAI-compatible API credentials are stored in Windows Credential Manager, never in ordinary JSON settings files.
- Credentials cannot be read back through the API; it only reports whether a supported credential is configured.
- Environment variables in `.env` take precedence. Credential Manager values are used when the matching secret environment value is empty.
- Credential Manager writes are Windows-only and fail closed when the secure Windows backend is unavailable.
