# Nexus AI

A React + TypeScript dashboard prototype for a local Ollama-powered agent workspace.
The current dashboard is presentation-only; Ollama connection and agent actions are
not wired up yet.

## Run locally

```powershell
cd nexus-ai
npm install
npm run dev
```

## Project structure

- `src/App.tsx` — dashboard layout and screen-level interactions.
- `src/index.css` — Tailwind entry point and global browser styles.
- `src/main.tsx` — React application entry point.
- `vite.config.ts` — Vite, React, and Tailwind CSS integration.

Run `npm run build` to type-check and create a production build, or `npm run lint`
to run Oxlint.
