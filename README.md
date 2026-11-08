# NEXUS AI

NEXUS AI is a local-first AI workspace with a shared Provider Manager for native Ollama (local/Kaggle) and optional OpenAI-compatible inference endpoints.
The repository's integrated application is in `backend/` and `frontend/`.

## Documentation

- [English guide](README.en.md)
- [O‘zbekcha qo‘llanma](README.uz.md)
- [Terminal commands and workflows](terminal%20commands.md)
- [Windows desktop launcher (English)](README.en.md#windows-desktop-launcher-stage-2)
- [Windows desktop launcher (O‘zbekcha)](README.uz.md#windows-desktop-launcher-stage-2)
- [MIT License](LICENSE)

## Current status

The dashboard can check Ollama connectivity and list installed models. The
optional Kaggle panel can launch a private Kaggle notebook and select its Ollama
runtime when ready; it requires Kaggle/ngrok credentials. Chat, agent execution,
UI model downloads, and workflows are not implemented.

## Repository layout

```text
backend/   FastAPI API, local/remote Ollama and Kaggle integration
frontend/  React + TypeScript dashboard
nexus-ai/  Earlier standalone UI prototype
```
