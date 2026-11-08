# NEXUS AI — O‘zbekcha

NEXUS AI — kompyuteringizdagi Ollama xizmati va o‘rnatilgan modellar holatini
ko‘rsatadigan, avvalo lokal ishlashga mo‘ljallangan dashboard. FastAPI backend
brauzerdagi interfeys bilan Ollama o‘rtasida API gateway vazifasini bajaradi.

> **Loyiha holati:** Lokal dashboard, backend health/status endpointlari,
> Ollama modellarini ko‘rish, ixtiyoriy Kaggle GPU boshqaruvi va lokal workspace Explorer ishlaydi.
> Kaggle uchun operator o‘z hisob ma’lumotlari va notebook secret’larini
> sozlashi kerak. Ollama bilan streaming chat va suhbat tarixini saqlash mavjud. Agent Runtime dastlabki versiyasi mavjud: agent faqat ruxsat berilgan workspace matnli fayllarini o‘qiy oladi. Workflow funksiyalari hali mavjud emas. Agentga aniq fayllar uchun read ruxsatini berish va chatga tanlangan fayllarni kontekst sifatida biriktirish mavjud.
> Ollama modellarini UI orqali yuklash va o‘chirish mavjud.

Loyiha [MIT litsenziyasi](LICENSE) ostida tarqatiladi.

## Talablar

- Windows 10/11, macOS yoki Linux
- Python 3.10 yoki undan yangi
- Node.js 20 yoki undan yangi (`npm` bilan)
- Lokal modellar holati uchun o‘rnatilgan va ishlayotgan Ollama

## Lokal ishga tushirish

### 1. Ollama’ni ishga tushirish

Ollama’ni <https://ollama.com> saytidan o‘rnating va ilovani ishga tushiring.
Agar Ollama hali ishlamayotgan bo‘lsa, alohida terminalda `ollama serve`
buyrug‘ini bajaring. Model yuklab oling:

```powershell
ollama pull llama3.2
ollama list
```

Ollama API’ning standart manzili: `http://127.0.0.1:11434`.

### 2. Backend’ni ishga tushirish

Repository root papkasida PowerShell oching:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`.env` faylini faqat bir marta yarating. U mavjud bo‘lsa, qayta ustidan
yozmang — ichidagi lokal sozlamalar va maxfiy qiymatlarni saqlang.

PowerShell virtual muhitni faollashtirishni bloklasa, shu PowerShell oynasida
quyidagini bajarib, muhitni yana faollashtiring:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Backend manzili: <http://127.0.0.1:8000>. API hujjatlari:
<http://127.0.0.1:8000/docs>.

### 3. Frontend’ni ishga tushirish

Ikkinchi PowerShell oynasini repository root papkasida oching:

```powershell
cd frontend
npm ci
npm run dev
```

Brauzerda <http://127.0.0.1:5173/> manzilini oching.

Frontend standart holatda `http://127.0.0.1:8000` API’ga ulanadi. Manzilni
o‘zgartirish uchun `frontend/.env.local` faylini yarating:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Frontend environment o‘zgaruvchilarini yangilagandan keyin Vite’ni qayta
ishga tushiring.

## Sozlamalar

Backend sozlamalari `backend/.env` faylidan o‘qiladi:

| O‘zgaruvchi | Vazifasi | Standart qiymat |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama HTTP API manzili | `http://127.0.0.1:11434` |
| `FRONTEND_ORIGINS` | Vergul bilan ajratilgan CORS manzillari | Vite localhost manzillari |
| `REQUEST_TIMEOUT_SECONDS` | Ollama so‘rovi kutish vaqti | `8` |
| `KAGGLE_USERNAME` | Kaggle username | Bo‘sh |
| `KAGGLE_KEY` | Kaggle API token | Bo‘sh |
| `KAGGLE_KERNEL_NAME` | Maxfiy Kaggle kernel nomi | `nexus-ollama-server` |
| `NGROK_DOMAIN` | `https://` siz ngrok statik domeni | Bo‘sh |
| `TUNNEL_USER` | Tunnel basic-auth foydalanuvchisi | `nexus` |
| `TUNNEL_PASSWORD` | Kuchli tunnel paroli | Bo‘sh |

Kaggle notebook uchun Kaggle Notebook Secrets’da `NGROK_TOKEN` va
`TUNNEL_PASSWORD` ham bo‘lishi kerak. Backend’dagi tunnel paroli Kaggle
Secret’dagi qiymat bilan bir xil bo‘lsin. `.env`, API token, ngrok token va
parollarni Git’ga qo‘shmang.

## Lokal Workspace

Explorer standart holatda foydalanuvchining `~/NexusWorkspace` papkasidan foydalanadi. Boshqa papkani tanlash uchun backend muhitida `NEXUS_WORKSPACE_ROOT` o‘zgaruvchisini belgilang. API yo‘llari workspace ildizidan tashqariga chiqishni rad etadi; ramziy havolalar ro‘yxatda ko‘rsatilmaydi. Matnli fayllarni ochish/tahrirlash limiti 2 MB, yuklash limiti 10 MB. Fayl o‘chirish mavjud emas. Agent ruxsatlari default holatda bo‘sh; har bir agentga faqat alohida tanlangan fayllar uchun read ruxsati beriladi.

## API endpointlari

Interfeys mavzusi va ovoz effektlari `backend/.nexus/preferences.json` faylida lokal saqlanadi. Bu fayl `.gitignore` orqali repozitoriyga kiritilmaydi.


| Method | Manzil | Vazifasi |
|---|---|---|
| `GET` | `/api/health` | Backend javob berayotganini tekshirish |
| `GET` | `/api/ollama/status` | Tanlangan Ollama runtime holatini tekshirish |
| `GET` | `/api/ollama/models` | Tanlangan Ollama runtime’dagi modellarni olish |
| `POST` | `/api/ollama/models/pull` | Modelni Ollama orqali oqimli progress bilan yuklash; body: `{"name":"llama3.2"}` |
| `DELETE` | `/api/ollama/models` | Modelni o‘chirish; body: `{"name":"llama3.2"}` |
| `GET` | `/api/kaggle/status` | Kaggle ishga tushishi va ulanish holatini olish |
| `GET` | `/api/workspace/tree` | Workspace papkasidagi fayl va papkalar ro‘yxati |
| `GET` | `/api/workspace/file` | Matnli faylni o‘qish |
| `GET` | `/api/workspace/asset` | Rasm faylini xavfsiz preview qilish |
| `POST` | `/api/workspace/file` | Yangi matnli fayl yaratish |
| `PUT` | `/api/workspace/file` | Matnli faylni saqlash |
| `POST` | `/api/workspace/directory` | Papka yaratish |
| `POST` | `/api/workspace/upload` | Faylni base64 orqali yuklash |
| `GET` | `/api/agents/{agent_id}/permissions` | Agentning aniq fayllarga read ruxsatlarini ko‘rish |
| `POST` | `/api/agents/{agent_id}/permissions/read` | Agentga bitta workspace faylini o‘qish ruxsatini berish |
| `DELETE` | `/api/agents/{agent_id}/permissions/read?path=notes.md` | Fayl uchun read ruxsatini bekor qilish |
| `POST` | `/api/agents/{agent_id}/context` | Ruxsat berilgan tanlangan fayllarni agent konteksti uchun olish |
| `POST` | `/api/agents/{agent_id}/run` | Agentni ishga tushirish; faqat read-grant tekshiruvidan o‘tgan `workspace_read_file` vositasi mavjud |
| `GET` | `/api/chat/conversations` | Suhbatlar ro‘yxatini olish |
| `GET` | `/api/chat/conversations/{conversation_id}` | Suhbat tarixini olish |
| `DELETE` | `/api/chat/conversations/{conversation_id}` | Suhbatni o‘chirish |
| `POST` | `/api/chat/stream` | Ollama bilan streaming chat; body: model, message, conversation_id?, agent_id?, paths? |
| `GET` | `/api/preferences` | Interfeys mavzusi va ovoz sozlamalarini olish |
| `PUT` | `/api/preferences` | Interfeys mavzusi va ovoz sozlamalarini saqlash; body: `{"theme":"dark","sound_enabled":false}` |
| `POST` | `/api/kaggle/start` | Kaggle runtime’ni boshlash; body: `{"model":"llama3.2"}` |
| `POST` | `/api/kaggle/mode` | `local` yoki tayyor `kaggle` runtime tanlash |

## Build va tekshiruv

`frontend/` ichida:

```powershell
npm run build
```

`backend/` ichida, virtual muhit faollashtirilgan holda:

```powershell
python -m compileall -q app
```

Lokal API’ni tez tekshirish:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/ollama/status
Invoke-RestMethod http://127.0.0.1:8000/api/ollama/models
```

To‘liq copy/paste buyruqlar va ishlash sxemalari:
[Terminal buyruqlari va sxemalari](terminal%20commands.md).

## Repository tuzilmasi

```text
backend/   FastAPI API, Ollama/Kaggle service’lari, schema va notebook shabloni
frontend/  React + TypeScript dashboard
nexus-ai/  Avvalgi mustaqil UI prototipi (integratsiyalangan ilova emas)
```


### Agent access modes, isolation va Docker sandbox

Access Control endpointlari:

- `GET /api/agents/{agent_id}/control` — joriy rejim va izolyatsiya holati.
- `PUT /api/agents/{agent_id}/control/mode` — `read_only`, `approval_required`, `autopilot` yoki `locked` rejimini tanlash.
- `POST /api/agents/{agent_id}/isolate` — agentni qulflash, faol Ollama so‘rovini bekor qilish va mavjud sandbox konteynerini to‘xtatishga urinish.
- `POST /api/agents/{agent_id}/release` — izolyatsiyadan chiqarish; xavfsiz `read_only` rejimiga qaytaradi.

Docker sandbox endpointlari:

- `GET /api/agents/{agent_id}/sandbox` — Docker sandbox holati.
- `POST /api/agents/{agent_id}/sandbox/start` — body: `{"paths":["notes.md"]}`; faqat agentga oldindan read ruxsati berilgan fayllarning alohida nusxasi bilan konteyner yaratadi.
- `POST /api/agents/{agent_id}/sandbox/stop` — konteynerni majburan to‘xtatib, vaqtinchalik nusxalarni o‘chiradi.

Sandbox uchun Docker Engine va oldindan yuklangan image kerak. Standart image `python:3.12-slim`; uni hostda oldindan `docker pull python:3.12-slim` bilan yuklang. Image yoki Docker CLI nomini mos ravishda `NEXUS_SANDBOX_IMAGE` va `NEXUS_DOCKER_BINARY` orqali o‘zgartirish mumkin. NEXUS image’ni o‘zi internetdan yuklamaydi; `--pull=never` ishlatiladi.

Konteyner `--network none`, read-only root filesystem, faqat read-only grant snapshot, non-root UID, barcha Linux capabilities olib tashlangan holat, `no-new-privileges`, 512 MB RAM, 1 CPU va 64 process limiti bilan ishga tushadi. Host workspace ildizi, Docker socket va boshqa host papkalari konteynerga mount qilinmaydi. `/tmp` 64 MB cheklangan tmpfs.

**Muhim:** bu birinchi sandbox bosqichi konteynerni xavfsiz tayyorlaydi va lifecycle’ni boshqaradi, lekin hozircha Agent Runtime ichidagi model chaqiruvlarini konteynerga ko‘chirmaydi; konteyner ichida faqat kutib turuvchi jarayon ishlaydi. Shell yoki kod bajarish vositasi yo‘q. Agent Runtime hanuz faqat ruxsatli matnli faylni o‘qiydi. `autopilot` ham hozircha shu tor vakolat doirasida; `approval_required` yozish amallari qo‘shilganda tasdiqlash darvozasi bo‘ladi. Docker mavjud bo‘lmasa, sandbox start xato bilan to‘xtaydi va host rejimiga fallback qilmaydi.
