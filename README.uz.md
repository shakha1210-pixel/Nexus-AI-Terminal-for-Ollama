# NEXUS AI — O‘zbekcha

NEXUS AI — kompyuteringizdagi Ollama xizmati va o‘rnatilgan modellar holatini
ko‘rsatadigan, avvalo lokal ishlashga mo‘ljallangan dashboard. FastAPI backend
brauzerdagi interfeys bilan Ollama o‘rtasida API gateway vazifasini bajaradi.

> **Loyiha holati:** Lokal dashboard, backend health/status endpointlari,
> Ollama modellarini ko‘rish, ixtiyoriy Kaggle GPU boshqaruvi va lokal workspace Explorer ishlaydi.
> Kaggle uchun operator o‘z hisob ma’lumotlari va notebook secret’larini
> sozlashi kerak. Ollama bilan streaming chat va suhbat tarixini saqlash mavjud. Agent Runtime dastlabki versiyasi mavjud: agent faqat ruxsat berilgan workspace matnli fayllarini o‘qiy oladi. Workflow funksiyalari hali mavjud emas. Agentga aniq fayllar uchun read ruxsatini berish va chatga tanlangan fayllarni kontekst sifatida biriktirish mavjud.
> Ollama modellarini UI orqali yuklash va o‘chirish mavjud. Provider Manager hozir native Ollama (local/Kaggle) va ixtiyoriy OpenAI-compatible API’ni umumiy interfeysga birlashtiradi; Chat va Agent bir xil faol provider/model tanlovidan foydalanadi. Anthropic va Gemini adapterlari keyingi bosqich uchun rejalashtirilgan. Provider Manager hozir native Ollama (local/Kaggle) va ixtiyoriy OpenAI-compatible API’ni umumiy interfeysga birlashtiradi; Chat va Agent bir xil faol provider/model tanlovidan foydalanadi. Anthropic va Gemini adapterlari keyingi bosqich uchun rejalashtirilgan.

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
| `OPENAI_COMPATIBLE_BASE_URL` | OpenAI-compatible API manzili, odatda `https://host/v1` | Bo‘sh |
| `OPENAI_COMPATIBLE_API_KEY` | Provider API kaliti; faqat backend’da saqlanadi | Bo‘sh |
| `OPENAI_COMPATIBLE_BASE_URL` | OpenAI-compatible API manzili, odatda `https://host/v1` | Bo‘sh |
| `OPENAI_COMPATIBLE_API_KEY` | Provider API kaliti; faqat backend’da saqlanadi | Bo‘sh |

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
| `GET` | `/api/agents/{agent_id}/approvals` | Agent uchun kutilayotgan fayl tahriri takliflarini ko‘rish |
| `POST` | `/api/agents/{agent_id}/approvals/{request_id}/decision` | Taklifni tasdiqlash yoki rad etish; body: `{"approve":true}` yoki `{"approve":false}` |
| `GET` | `/api/chat/conversations` | Suhbatlar ro‘yxatini olish |
| `GET` | `/api/chat/conversations/{conversation_id}` | Suhbat tarixini olish |
| `DELETE` | `/api/chat/conversations/{conversation_id}` | Suhbatni o‘chirish |
| `POST` | `/api/chat/stream` | Tanlangan provider bilan streaming chat; body: provider_id?, model, message, conversation_id?, agent_id?, paths? |
| `GET` | `/api/providers/catalog` | Konfiguratsiyalangan providerlar, ulanish holati va modellari |
| `GET` | `/api/providers/active` | Umumiy faol provider tanlovini olish |
| `PUT` | `/api/providers/active` | Chat va Agent uchun umumiy provider tanlash; body: `{"provider_id":"ollama"}` yoki `{"provider_id":"openai-compatible"}` |
| `GET` | `/api/providers/policy` | Fallback switching siyosatini olish |
| `PUT` | `/api/providers/policy` | Fallback switching siyosatini saqlash |
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


### Agent access modes va isolation

- `GET /api/agents/{agent_id}/control` — joriy rejim va izolyatsiya holati.
- `PUT /api/agents/{agent_id}/control/mode` — `read_only`, `approval_required`, `autopilot` yoki `locked` rejimini tanlash.
- `POST /api/agents/{agent_id}/isolate` — agentni qulflash va faol provider so‘rovini bekor qilish.
- `POST /api/agents/{agent_id}/release` — izolyatsiyadan chiqarish; xavfsiz `read_only` rejimiga qaytaradi.

`approval_required` rejimida agentga `workspace_propose_file_edit` vositasi beriladi. Bu vosita faqat mavjud UTF-8 matnli faylni almashtirish taklifini yaratadi; faylni o‘zi yozmaydi. Taklif Approval Queue’da to‘liq matn va fayl yo‘li bilan ko‘rsatiladi. Foydalanuvchi tasdiqlasa, aynan shu mazmun bir marta yoziladi; rad etsa yoki 10 daqiqada ko‘rib chiqilmasa, bajarilmaydi. Taklif yaratilgandan keyin asl fayl o‘zgargan bo‘lsa, tasdiq bekor qilinadi va yangi taklif talab etiladi. Hozircha yangi fayl yaratish, o‘chirish, papka o‘zgartirish yoki ko‘p faylli amallar tasdiqlash vositasida mavjud emas.

`autopilot` hamon faqat mavjud read-only vositalar bilan cheklangan. Agentga shell yoki tashqi tarmoq vositasi berilmagan. Provider Manager orqali tanlangan modelning tool-calling imkoniyati tekshiriladi; qo‘llab-quvvatlanmasa Agent ishga tushmaydi. Provider Manager orqali tanlangan modelning tool-calling imkoniyati tekshiriladi; qo‘llab-quvvatlanmasa Agent ishga tushmaydi. Tasdiqlash API’si hozirgi local-first backend arxitekturasiga tayanadi; backendni ishonchsiz tarmoqka ochmang, chunki autentifikatsiya qatlami hali mavjud emas. Izolyatsiya faol Ollama HTTP so‘rovini bekor qiladi, ammo bu alohida OS/container sandbox yoki barcha host tarmog‘ini uzish bilan teng emas.


## Windows desktop launcher (Stage 2)

Desktop rejimi uchun avval backend va desktop bog‘liqliklarini o‘rnating:

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install -r desktop/requirements.txt
```

Frontend build tayyor bo‘lsa, repository root papkasidan ishga tushiring:

```powershell
python desktop/launcher.py
```

- `--browser` — PyWebView o‘rniga standart brauzerni ochadi.
- `--dev` — Vite dev serverini (5173-port) ham ishga tushiradi.
- `--port 8123` — FastAPI portini o‘zgartiradi (standart: 8000).
- Windows’da WebView2 Runtime topilmasa, launcher rasmiy runtime’ni o‘rnatish bo‘yicha ko‘rsatma beradi va brauzerga o‘tadi.
- Ollama alohida o‘rnatiladi; launcher uni paket ichiga qo‘shmaydi va avtomatik ishga tushirmaydi.
- Tray menyusidan oynani qayta ochish yoki dasturni yopish mumkin. PyWebView/Pillow/pystray bo‘lmasa, brauzer fallback ishlatiladi.
- Bir vaqtning o‘zida ikkinchi NEXUS nusxasini ochish Windows named mutex orqali bloklanadi.

PyWebView, tray va WebView2 ishlashini haqiqiy Windows 10/11 qurilmasida tekshirish kerak; Linux CI bu platforma integratsiyasini to‘liq tasdiqlamaydi.
