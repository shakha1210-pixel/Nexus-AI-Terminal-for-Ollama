# NEXUS Development Log

This file is the chronological record of meaningful project decisions, implementation changes, verification, and next steps.

## 2026-11-11 — Documentation baseline and product direction

### Decisions
- Keep project documentation intentionally compact: README.md, README.uz.md, and this log.
- README.md is the canonical current-state reference; README.uz.md is its Uzbek counterpart.
- Use this log for dated history. Do not turn it into a duplicate of the README.
- Keep NEXUS focused on being a universal AI workspace where users connect their own providers and services.
- Preserve the existing modular application and evolve it incrementally; start with a modular monolith.
- The intended default UI is a premium, minimal, chat-first experience. Move secondary tools and advanced configuration into navigation and Settings.
- Distinguish implemented capabilities from planned product direction in all documentation.

### Completed
- [x] Reviewed the repository's existing README files and found conflicting feature-status descriptions.
- [x] Identified the existing integrated stack: FastAPI backend, React/TypeScript/Vite frontend, PyWebView desktop launcher, provider adapters, chat, workspace, and initial agent runtime.
- [x] Created a dedicated documentation branch so these changes do not overlap with the already-open UI pull request.
- [x] Consolidated the documentation structure around two README files and one development log.

### In progress
- [x] Opened [PR #31](https://github.com/shakha1210-pixel/Nexus-AI-Terminal-for-Ollama/pull/31) for documentation review.
- [ ] Review the rendered Markdown and repository checks before merging.

### Planned
- [ ] Continue refining the primary application screen around the premium chat-first layout. First implementation pass is in draft [PR #32](https://github.com/shakha1210-pixel/Nexus-AI-Terminal-for-Ollama/pull/32).
  - First pass: chat is the default view, navigation is simplified, conversation history has its own compact panel, advanced context and attachments are collapsed, and welcome prompts are localized.
  - Initial frontend CI found one unused import; it was removed and the checks were restarted.
- [ ] Keep conversation history and primary navigation in a compact sidebar.
- [ ] Place API connections, credentials, permissions, appearance, and advanced configuration in Settings.
- [ ] Expand dynamic provider/API connection management.
- [ ] Improve the workspace editor and define the integrated terminal scope.
- [ ] Extend the agent runtime and permission model carefully.
- [ ] Design and implement a safe user plugin system.

### Notes
- The current workspace is not yet a complete IDE.
- The current provider manager supports native Ollama and an OpenAI-compatible adapter; arbitrary protocols may require adapters.
- Kaggle is an optional user-configured compute integration, not a NEXUS-hosted inference service.
- No application code or UI behavior was changed in this documentation task.
- The first chat-first UI implementation is being developed separately from this documentation branch to keep review scopes isolated.

## 2026-11-12 — Long-term platform architecture added

### Decisions
- Record the proposed multi-entry architecture: Windows desktop launcher, React + TypeScript workspace web app, and an optional future Next.js or Astro landing site connecting to a FastAPI API gateway.
- Document logical backend capabilities: Auth/RBAC/workspaces, provider management, chat/SSE/history, RAG, agent runtime, workflows, billing/usage metering, and integrations (GitHub, Slack, Drive/Notion, Webhooks, MCP).
- Record PostgreSQL + pgvector, Redis, S3/R2, and Celery/arq workers as candidate future infrastructure, not current dependencies.
- Keep the modular-monolith-first strategy. The diagram expresses logical boundaries and does not mandate one deployable microservice per box.
- Clearly distinguish the existing provider foundation (Ollama and OpenAI-compatible adapters, plus user-configured Kaggle runtime integration) from the planned dynamic provider platform.

### Completed
- [x] Added the target platform diagram and implementation-status notes to README.md.
- [x] Added the corresponding Uzbek architecture section to README.uz.md.
- [x] Explicitly marked authentication/RBAC, RAG, workflows, billing, broad integrations, and the proposed data/worker infrastructure as planned rather than implemented.

### Planned
- [ ] Define phased milestones and acceptance criteria for each target capability before implementation.
- [ ] Decide whether/when a separate public landing site is needed and select Next.js or Astro based on concrete requirements.
- [ ] Design the RAG data lifecycle, workspace isolation, access controls, and deletion behavior before selecting production storage.
- [ ] Define API authentication, RBAC roles, tenant/workspace boundaries, and audit requirements before exposing remote access.

