# NEXUS

**NEXUS is a local-first, universal AI workspace.** It brings AI conversations, model/provider connections, agent-assisted work, and a local workspace into one desktop-oriented environment. Users choose the models and services they connect; NEXUS provides a consistent workspace around them.

> **Product direction:** NEXUS is not intended to become a model provider or a direct Cursor clone. Its role is to provide a flexible workspace where users can connect their own API-compatible services and use them alongside local models and workspace tools.

- [O‘zbekcha hujjat](README.uz.md)
- [Development log](DEVELOPMENT_LOG.md)
- [Terminal commands and workflows](terminal%20commands.md)
- [MIT License](LICENSE)

---

## Product principles

- **User choice:** users choose their model, provider, endpoint, and compute environment.
- **One workspace:** chat, agents, files, and model connections should work together rather than feel like unrelated products.
- **Local-first:** local inference and local workspace data remain first-class options.
- **Simple core:** evolve the existing modular application before considering distributed services or unnecessary infrastructure.
- **Safe by default:** credentials must not be exposed in ordinary settings, logs, or client responses; agent access must remain permission-scoped.
- **Progressive complexity:** keep the default experience calm and approachable; expose advanced controls only when needed.

## Current implementation status

This section describes what exists in the repository today. Planned product direction is listed separately in the roadmap.

### Available foundation

- FastAPI backend and React 18 + TypeScript + Vite frontend.
- PyWebView desktop launcher and Windows packaging/build workflow.
- Provider abstraction and manager for native Ollama (local/Kaggle runtime selection) and an OpenAI-compatible endpoint.
- Streaming chat and conversation history.
- Provider/model selection shared by chat and agent flows.
- Workspace Explorer with scoped file and directory operations.
- Agent runtime with explicit workspace read permissions, control modes, isolation controls, and approval flow for supported file-edit proposals.
- Kaggle notebook/runtime integration, requiring the user's own Kaggle and tunnel configuration.
- Credential-storage foundation using the system keyring where supported.
- Backend and frontend CI/build workflows.

### Current limitations

- The provider catalogue is not yet a fully dynamic, user-extensible connection manager.
- Arbitrary API protocols may require a dedicated adapter; an endpoint URL alone does not guarantee protocol compatibility.
- The workspace is not yet a full IDE: a complete editor experience, integrated terminal, language-server support, debugger, and mature Git UI are not established features.
- The plugin SDK, plugin loader, and user-facing plugin lifecycle are not yet implemented as a complete system.
- Agent capabilities are deliberately limited by the current tool and permission model; this is not an unrestricted autonomous coding agent.
- Backend authentication and deployment hardening need further work before exposing the service to untrusted networks.
- Desktop shell behavior and installer flows still require validation on real supported Windows machines.

## Product experience and UI/UX direction

The intended default screen is a **premium, minimal AI chat workspace**.

- The central area is dedicated to the active conversation.
- A clear composer anchors the bottom of the chat, with model/connection context close at hand.
- Conversation history and primary navigation live in a compact side panel.
- Workspace, files, agents, and plugins are available from navigation without dominating the default chat view.
- API connections, credentials, permissions, appearance, and advanced configuration belong in Settings.
- Contextual actions should appear when relevant instead of keeping every tool visible at all times.
- Chat and workspace should remain connected: users should be able to provide files as context and open agent results in the workspace.

This is a **design direction**, not a claim that the current UI already implements it.

## System architecture

The current application is a modular Python/FastAPI backend with a React frontend. The practical goal is to strengthen its existing boundaries rather than replace the working foundation wholesale.

~~~text
NEXUS
├── Desktop shell
│   └── PyWebView launcher / Windows packaging
├── Frontend
│   ├── Chat and conversation history
│   ├── Provider and model controls
│   ├── Agent panel
│   ├── Workspace Explorer
│   └── Settings and diagnostics
└── Backend (FastAPI)
    ├── Providers
    │   ├── Provider base / registry / manager
    │   └── Ollama and OpenAI-compatible adapters
    ├── Chat and streaming
    ├── Agents
    │   ├── Runtime and tools
    │   ├── Access permissions
    │   ├── Approval flow
    │   └── Control and isolation
    ├── Workspace services
    ├── Secrets and preferences
    └── Optional Kaggle integration
~~~

### Target architectural evolution

The following are architectural directions, not existing directory names or completed modules:

- **Core:** shared configuration, events, storage boundaries, and security utilities.
- **Gateway / Connections:** dynamic connection configuration, protocol adapters, model metadata, health checks, and provider routing.
- **Workspace:** richer editor, explorer, integrated terminal, Git workflows, and session/context management.
- **Agent Engine:** extensible tools, context management, permission checks, approvals, and execution controls.
- **Plugin System:** documented extension contract, manifest, loader, lifecycle, and user-managed plugins.

Start with a **modular monolith**. Extract services only when real scaling, isolation, or maintenance needs justify it.

### Proposed platform topology

The diagram below records the **long-term platform target**. It is a planning architecture, not a description of services or infrastructure already deployed. The existing FastAPI application remains the starting point; implement these boundaries incrementally inside a modular monolith before considering independent services.

~~~text
Desktop (Windows launcher) ─┐
Web (React + TypeScript) ────┼──► API Gateway (FastAPI)
Landing (Next.js or Astro) ──┘          │
                                        ├── Auth + RBAC + Workspaces
                                        ├── Provider Manager (existing foundation):
                                        │     Ollama / Kaggle integration / OpenAI-compatible
                                        ├── Chat Service: SSE streaming, conversation history
                                        ├── RAG Service: upload → chunk → embedding → pgvector
                                        ├── Agent Runtime: tool calling, sandbox, approval
                                        ├── Workflow Engine: trigger → step → action
                                        ├── Billing: Stripe + usage metering
                                        └── Integrations: GitHub, Slack, Drive/Notion,
                                              Webhooks, MCP
                                        │
                  Postgres + pgvector · Redis (queue/cache)
                  S3/R2 (file storage) · Worker (Celery or arq)
~~~

**Implementation status and boundaries**

- **Existing foundation:** Windows/PyWebView desktop launcher, React + TypeScript + Vite application, FastAPI backend, provider abstraction/manager, Ollama and OpenAI-compatible adapters, Kaggle runtime integration, chat streaming/history, workspace operations, and an initial agent runtime.
- **Planned application capabilities:** dedicated API gateway boundary, authentication and role-based access control (RBAC), multi-workspace support, RAG pipeline, workflow engine, usage metering/billing, and broader integrations.
- **Planned infrastructure choices:** PostgreSQL with pgvector, Redis, S3-compatible object storage (S3/R2), and background workers (Celery or arq). These are candidate components, not current runtime requirements.
- **Planned web entry points:** keep the current React/Vite application as the workspace UI. A separate Next.js or Astro landing site is an optional future public-facing entry point; choose one only when there is a concrete need.
- **Provider note:** the current provider foundation covers Ollama and OpenAI-compatible APIs, with Kaggle as a user-configured runtime integration. It is not yet a fully dynamic provider platform.

The target diagram describes logical responsibilities, not a requirement to deploy every box as a separate microservice. Keep service boundaries modular and deploy together until operational needs justify separation.


## Technology stack

| Area | Current technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React 18, TypeScript, Vite |
| Desktop | PyWebView |
| Local model runtime | Ollama |
| Remote model interface | OpenAI-compatible API adapter |
| Optional compute integration | Kaggle notebooks and configured tunnel |
| Credential storage | Python keyring / operating-system credential store where supported |
| Packaging and CI | GitHub Actions, Windows build/installer scripts |

## Roadmap

Statuses are intentionally explicit. A planned item must not be described as implemented until it is present and verified in code.

### Foundation
- [x] Establish FastAPI + React application foundation.
- [x] Add Ollama and OpenAI-compatible provider adapters.
- [x] Add streaming chat and conversation history.
- [x] Add initial workspace Explorer and scoped file operations.
- [x] Add initial agent runtime, access controls, and approval mechanisms.
- [x] Add desktop launcher and Windows packaging workflow.

### Next priorities
- [ ] Align the current UI with the premium, chat-first navigation direction.
- [ ] Reconcile documentation and feature status with the actual code after each meaningful change.
- [ ] Expand provider connections beyond the current fixed provider configuration.
- [ ] Improve workspace editing and establish the integrated terminal direction.
- [ ] Strengthen agent tool contracts, context handling, and permission boundaries.
- [ ] Define and implement a safe, documented user plugin system.
- [ ] Improve backend authentication and deployment security before network exposure.
- [ ] Expand automated tests and real-device desktop validation.

## Local development

### Requirements

- Python 3.10 or later.
- Node.js 20 or later (npm included).
- Ollama installed and running if using local models.
- Windows 10/11, macOS, or Linux for development; some desktop packaging behavior is Windows-specific.

### Backend

From the repository root:

~~~powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

If the virtual environment is already active or the .env file exists, do not recreate or overwrite local configuration unnecessarily.

Backend API documentation: <http://127.0.0.1:8000/docs>

### Frontend

Open a second terminal at the repository root:

~~~powershell
cd frontend
npm ci
npm run dev
~~~

Open <http://127.0.0.1:5173/>.

The frontend uses http://127.0.0.1:8000 by default. To override it, create frontend/.env.local:

~~~env
VITE_API_BASE_URL=http://127.0.0.1:8000
~~~

### Build checks

From frontend/:

~~~powershell
npm run build
~~~

From backend/ with its virtual environment active:

~~~powershell
python -m compileall -q app
~~~

See [terminal commands and workflows](terminal%20commands.md) for additional project commands.

## Configuration and security notes

- Backend configuration is read from backend/.env; use backend/.env.example as the starting point.
- Never commit API keys, Kaggle credentials, tunnel tokens, passwords, or local .env files.
- Use the supported credential store for secrets where available. Do not add secret values to frontend state, ordinary preference files, logs, or diagnostic output.
- Kaggle runtime use requires the user's own Kaggle credentials and notebook secrets; it is an optional compute integration, not a NEXUS-hosted model service.
- Keep the backend bound to localhost for local use unless authentication and deployment protections have been deliberately configured. The current backend should not be exposed to an untrusted network.

## Repository layout

~~~text
backend/       FastAPI application, providers, routers, and services
frontend/      React + TypeScript application
desktop/       PyWebView launcher and desktop integration
scripts/       Build and Windows preflight scripts
.github/       CI workflows
nexus-ai/      Earlier standalone UI prototype; not the integrated application
~~~

## Documentation maintenance

The project uses two README files and one chronological development log:

- README.md is the canonical project overview and current-state reference.
- README.uz.md is its Uzbek-language counterpart.
- DEVELOPMENT_LOG.md records dated decisions, completed work, ongoing tasks, and next steps.

After a meaningful change:
1. Implement and verify the change.
2. Update both README files if the current state, architecture, setup, or roadmap changed.
3. Append a dated entry to DEVELOPMENT_LOG.md.
4. Keep completed, in-progress, and planned work clearly separated.

The README describes the **current verified state**. The development log preserves the **history of how the project got there**.
