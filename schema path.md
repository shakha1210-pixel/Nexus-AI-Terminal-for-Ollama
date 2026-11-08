Current repository structure

.
├── backend/
│   ├── app/
│   │   ├── routers/ollama.py
│   │   ├── schemas/ollama.py
│   │   ├── services/ollama_service.py
│   │   ├── config.py
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── services/api.ts
│   │   ├── types/ollama.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── index.html
│   └── package.json
└── README.md

The separate nexus-ai/ directory is an earlier standalone UI prototype, not part
of the integrated backend/frontend application.
