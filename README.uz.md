# NEXUS

**NEXUS — lokal ishlashga ustuvorlik beradigan universal AI workspace.** U AI suhbatlari, model/provider ulanishlari, agentlar yordamida ishlash va lokal workspace'ni yagona desktop muhitida birlashtiradi. Foydalanuvchi qaysi model va xizmatlarga ulanishni o‘zi tanlaydi; NEXUS esa ular bilan ishlash uchun qulay va izchil muhitni taqdim etadi.

> **Loyiha yo‘nalishi:** NEXUS model provayderi yoki Cursor'ning to‘g‘ridan-to‘g‘ri nusxasi bo‘lishni maqsad qilmaydi. Uning vazifasi — foydalanuvchi o‘z API-compatible xizmatlarini, lokal modellarini va workspace vositalarini bir joyda ishlata oladigan moslashuvchan muhit yaratish.

- [English documentation](README.md)
- [Rivojlanish jurnali](DEVELOPMENT_LOG.md)
- [Terminal buyruqlari va ishlash qo‘llanmasi](terminal%20commands.md)
- [MIT litsenziyasi](LICENSE)

---

## Mahsulot tamoyillari

- **Tanlov erkinligi:** model, provider, endpoint va hisoblash muhitini foydalanuvchi tanlaydi.
- **Yagona workspace:** chat, agentlar, fayllar va model ulanishlari bir-biridan uzilgan mahsulotdek emas, o‘zaro bog‘langan holda ishlashi kerak.
- **Local-first:** lokal inference va lokal workspace ma'lumotlari asosiy imkoniyat bo‘lib qoladi.
- **Sodda yadro:** mavjud modulli ilovani rivojlantirish; zaruratsiz microservice yoki murakkab infratuzilma yaratmaslik.
- **Xavfsizlik standart holatda:** maxfiy kalitlar oddiy sozlamalar, loglar yoki client javoblarida oshkor bo‘lmasligi; agent ruxsatlari aniq chegaralangan bo‘lishi kerak.
- **Murakkablikni bosqichma-bosqich ochish:** odatiy interfeys sodda bo‘ladi, ilg‘or sozlamalar esa kerak bo‘lganda ochiladi.

## Hozirgi amalga oshirilgan holat

Bu bo‘lim repozitoriydagi mavjud kodni ifodalaydi. Kelajakdagi yo‘nalishlar roadmap'da alohida ko‘rsatilgan.

### Mavjud asos

- FastAPI backend va React 18 + TypeScript + Vite frontend.
- PyWebView desktop launcher hamda Windows build/installer jarayoni.
- Native Ollama (local/Kaggle runtime tanlovi) va OpenAI-compatible endpoint uchun provider abstraction va manager.
- Streaming chat va suhbatlar tarixi.
- Chat hamda agent oqimlarida umumiy provider/model tanlovi.
- Workspace Explorer va chegaralangan fayl/papka amallari.
- Agent runtime: workspace fayllarini o‘qish uchun aniq ruxsatlar, boshqaruv rejimlari, izolyatsiya boshqaruvi va qo‘llab-quvvatlangan fayl tahriri takliflari uchun tasdiqlash jarayoni.
- Kaggle notebook/runtime integratsiyasi; foydalanuvchining o‘z Kaggle va tunnel sozlamalarini talab qiladi.
- Qo‘llab-quvvatlanadigan platformalarda tizim keyring'idan foydalanadigan credential storage asosi.
- Backend va frontend uchun CI/build jarayonlari.

### Hozirgi cheklovlar

- Provider katalogi hali to‘liq dinamik va foydalanuvchi kengaytira oladigan connection manager emas.
- Ixtiyoriy API protokollari uchun alohida adapter kerak bo‘lishi mumkin; faqat endpoint URL kiritish protokol mosligini kafolatlamaydi.
- Workspace hali to‘liq IDE emas: mukammal editor, integratsiyalashgan terminal, language-server, debugger va to‘liq Git UI mavjud deb hisoblanmaydi.
- Plugin SDK, plugin loader va foydalanuvchi plugin'lari lifecycle'i hali to‘liq tizim sifatida yaratilmagan.
- Agent imkoniyatlari hozirgi tool va permission modeli bilan ataylab cheklangan; bu cheklanmagan avtonom coding agent emas.
- Backend authentication va deployment xavfsizligini kuchaytirish kerak; hozircha uni ishonchsiz tarmoqqa ochmaslik lozim.
- Desktop shell va installer jarayonlari haqiqiy qo‘llab-quvvatlanadigan Windows qurilmalarida tekshirilishi kerak.

## Mahsulot tajribasi va UI/UX yo‘nalishi

Asosiy ekran **premium, minimal va chat-first AI workspace** bo‘lishi ko‘zda tutilgan.

- Markaziy qism faol suhbat uchun ajratiladi.
- Pastda qulay prompt maydoni bo‘ladi; model va ulanish konteksti unga yaqin joylashadi.
- Suhbatlar tarixi va asosiy navigatsiya ixcham yon panelda turadi.
- Workspace, fayllar, agentlar va plugin'lar asosiy chatni egallab olmasdan navigatsiya orqali ochiladi.
- API ulanishlari, credential'lar, ruxsatlar, tashqi ko‘rinish va ilg‘or konfiguratsiyalar Settings ichida bo‘ladi.
- Barcha vositalarni doimiy ko‘rsatish o‘rniga, kerakli kontekstda tegishli amallar chiqariladi.
- Chat va workspace o‘zaro bog‘langan bo‘ladi: foydalanuvchi fayllarni kontekstga qo‘sha olishi va agent natijalarini workspace'da ochishi kerak.

Bu — **dizayn yo‘nalishi**, hozirgi interfeysda bularning barchasi tayyor degani emas.

## Tizim arxitekturasi

Hozirgi ilova React frontend va modullarga ajratilgan Python/FastAPI backend'dan tashkil topgan. Maqsad — ishlayotgan asosni birdan almashtirish emas, balki mavjud modullar chegaralarini mustahkamlash.

~~~text
NEXUS
├── Desktop shell
│   └── PyWebView launcher / Windows packaging
├── Frontend
│   ├── Chat va suhbatlar tarixi
│   ├── Provider va model boshqaruvi
│   ├── Agent paneli
│   ├── Workspace Explorer
│   └── Settings va diagnostika
└── Backend (FastAPI)
    ├── Providers
    │   ├── Provider base / registry / manager
    │   └── Ollama va OpenAI-compatible adapterlar
    ├── Chat va streaming
    ├── Agents
    │   ├── Runtime va tools
    │   ├── Access permissions
    │   ├── Approval flow
    │   └── Control va isolation
    ├── Workspace services
    ├── Secrets va preferences
    └── Ixtiyoriy Kaggle integratsiyasi
~~~

### Arxitekturani kelajakda rivojlantirish

Quyidagilar — arxitektura yo‘nalishlari; ular hozir mavjud papka nomlari yoki tayyor modullar degani emas:

- **Core:** umumiy konfiguratsiya, event'lar, storage chegaralari va security yordamchi vositalari.
- **Gateway / Connections:** dinamik connection konfiguratsiyasi, protokol adapterlari, model metadata, health-check va provider routing.
- **Workspace:** yaxshilangan editor, explorer, integratsiyalashgan terminal, Git workflow va session/context boshqaruvi.
- **Agent Engine:** kengaytiriladigan tools, context management, permission tekshiruvlari, tasdiqlash va bajarish nazorati.
- **Plugin System:** hujjatlashtirilgan extension contract, manifest, loader, lifecycle va foydalanuvchi boshqaradigan plugin'lar.

Boshlang‘ich yondashuv — **modular monolith**. Servislarni faqat real masshtablash, izolyatsiya yoki texnik xizmat ehtiyoji paydo bo‘lganda ajratamiz.

### Platformaning taklif etilayotgan arxitekturasi

Quyidagi diagramma NEXUS'ning **uzoq muddatli platforma maqsadini** ko‘rsatadi. Bu hozir ishga tushirilgan servislar yoki infratuzilma tavsifi emas, balki bosqichma-bosqich amalga oshiriladigan reja. Mavjud FastAPI ilovasi boshlang‘ich asos bo‘lib qoladi; alohida servislar yaratishdan oldin chegaralarni modular monolith ichida shakllantiramiz.

~~~text
Desktop (Windows launcher) ─┐
Web (React + TypeScript) ────┼──► API Gateway (FastAPI)
Landing (Next.js yoki Astro) ┘          │
                                        ├── Auth + RBAC + Workspaces
                                        ├── Provider Manager (mavjud asos):
                                        │     Ollama / Kaggle integratsiyasi / OpenAI-compatible
                                        ├── Chat Service: SSE streaming, suhbatlar tarixi
                                        ├── RAG Service: yuklash → chunk → embedding → pgvector
                                        ├── Agent Runtime: tool calling, sandbox, ruxsat tasdig‘i
                                        ├── Workflow Engine: trigger → step → action
                                        ├── Billing: Stripe + usage metering
                                        └── Integrations: GitHub, Slack, Drive/Notion,
                                              Webhooks, MCP
                                        │
                  Postgres + pgvector · Redis (queue/cache)
                  S3/R2 (fayl saqlash) · Worker (Celery yoki arq)
~~~

**Amalga oshirish holati va chegaralar**

- **Mavjud asos:** Windows/PyWebView desktop launcher, React + TypeScript + Vite ilovasi, FastAPI backend, provider abstraction/manager, Ollama va OpenAI-compatible adapterlari, Kaggle runtime integratsiyasi, chat streaming/tarixi, workspace amallari va dastlabki agent runtime.
- **Rejalashtirilgan ilova imkoniyatlari:** alohida API gateway chegarasi, autentifikatsiya va rollarga asoslangan ruxsatlar (RBAC), bir nechta workspace, RAG pipeline, workflow engine, foydalanish hisoboti/billing va kengroq integratsiyalar.
- **Rejalashtirilgan infratuzilma variantlari:** pgvector kengaytmali PostgreSQL, Redis, S3-compatible fayl ombori (S3/R2) va fon worker'lari (Celery yoki arq). Bular hozirgi ishga tushirish uchun talab emas, kelajakdagi variantlardir.
- **Kelajakdagi web kirish nuqtalari:** hozirgi React/Vite ilovasi workspace UI bo‘lib qoladi. Alohida Next.js yoki Astro landing sahifasi ommaviy sayt uchun kelajakdagi ixtiyoriy kirish nuqtasi; aniq ehtiyoj tug‘ilgandagina ulardan biri tanlanadi.
- **Provider izohi:** hozirgi asos Ollama va OpenAI-compatible API'larni, Kaggle esa foydalanuvchi sozlaydigan runtime integratsiyasini qamrab oladi. Bu hali to‘liq dinamik provider platformasi emas.

Diagrammadagi bloklar mantiqiy mas'uliyatlarni bildiradi; ularning har birini alohida microservice sifatida deploy qilish shart emas. Operatsion ehtiyoj isbotlanmaguncha modullarni birgalikda deploy qilinadigan modular monolith sifatida saqlaymiz.


## Texnologiyalar

| Yo‘nalish | Hozirgi texnologiya |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React 18, TypeScript, Vite |
| Desktop | PyWebView |
| Lokal model runtime | Ollama |
| Masofaviy model interfeysi | OpenAI-compatible API adapter |
| Ixtiyoriy compute integratsiyasi | Kaggle notebook va sozlangan tunnel |
| Credential storage | Python keyring / qo‘llab-quvvatlansa OS credential store |
| Packaging va CI | GitHub Actions, Windows build/installer skriptlari |

## Roadmap

Holatlar ataylab aniq ajratiladi. Rejalashtirilgan funksiya kodda mavjud bo‘lib, tekshirilmaguncha tayyor deb ko‘rsatilmaydi.

### Poydevor
- [x] FastAPI + React ilova asosini yaratish.
- [x] Ollama va OpenAI-compatible provider adapterlarini qo‘shish.
- [x] Streaming chat va suhbatlar tarixini qo‘shish.
- [x] Dastlabki workspace Explorer va chegaralangan fayl amallarini qo‘shish.
- [x] Dastlabki agent runtime, access control va approval mexanizmlarini qo‘shish.
- [x] Desktop launcher va Windows packaging jarayonini qo‘shish.

### Keyingi ustuvor vazifalar
- [ ] Hozirgi UI'ni premium, chat-first navigatsiya yo‘nalishiga moslashtirish.
- [ ] Har bir muhim o‘zgarishdan keyin hujjatlar va feature holatini real kod bilan muvofiqlashtirish.
- [ ] Provider ulanishlarini hozirgi qat'iy konfiguratsiyadan kengaytirish.
- [ ] Workspace editing'ni yaxshilash va integratsiyalashgan terminal yo‘nalishini belgilash.
- [ ] Agent tool contract, context handling va permission chegaralarini kuchaytirish.
- [ ] Xavfsiz va hujjatlashtirilgan user plugin tizimini ishlab chiqish.
- [ ] Tarmoqqa chiqarishdan oldin backend authentication va deployment xavfsizligini yaxshilash.
- [ ] Avtomatlashtirilgan testlar va haqiqiy qurilmadagi desktop tekshiruvlarini kengaytirish.

## Lokal ishlab chiqish

### Talablar

- Python 3.10 yoki undan yangi.
- Node.js 20 yoki undan yangi (npm bilan).
- Lokal model ishlatish uchun o‘rnatilgan va ishlayotgan Ollama.
- Ishlab chiqish uchun Windows 10/11, macOS yoki Linux; desktop packaging'ning ayrim qismlari Windows'ga xos.

### Backend

Repository root papkasidan:

~~~powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

Virtual muhit allaqachon faol yoki .env mavjud bo‘lsa, lokal konfiguratsiyani keraksiz qayta yaratmang yoki ustidan yozmang.

Backend API hujjatlari: <http://127.0.0.1:8000/docs>

### Frontend

Repository root papkasida ikkinchi terminal oching:

~~~powershell
cd frontend
npm ci
npm run dev
~~~

Brauzerda <http://127.0.0.1:5173/> manzilini oching.

Frontend standart holatda http://127.0.0.1:8000 manziliga ulanadi. O‘zgartirish uchun frontend/.env.local yarating:

~~~env
VITE_API_BASE_URL=http://127.0.0.1:8000
~~~

### Build tekshiruvlari

frontend/ ichida:

~~~powershell
npm run build
~~~

backend/ ichida, virtual muhit faol bo‘lganda:

~~~powershell
python -m compileall -q app
~~~

Qo‘shimcha buyruqlar uchun [terminal buyruqlari va ishlash qo‘llanmasi](terminal%20commands.md) bilan tanishing.

## Konfiguratsiya va xavfsizlik

- Backend konfiguratsiyasi backend/.env faylidan o‘qiladi; boshlang‘ich namuna sifatida backend/.env.example dan foydalaning.
- API key, Kaggle credential, tunnel token, parol va lokal .env fayllarini Git'ga qo‘shmang.
- Qo‘llab-quvvatlanadigan joyda maxfiy qiymatlarni credential store'da saqlang. Ularni frontend state, oddiy preferences fayllari, log yoki diagnostika natijalariga yozmang.
- Kaggle runtime foydalanuvchining o‘z Kaggle credential va notebook secret'larini talab qiladi; bu NEXUS tomonidan host qilinadigan model xizmati emas, ixtiyoriy compute integratsiyasidir.
- Authentication va deployment himoyasi ataylab sozlanmagan bo‘lsa, backend'ni localhost bilan cheklang. Hozirgi backend'ni ishonchsiz tarmoqqa ochmang.

## Repository tuzilmasi

~~~text
backend/       FastAPI ilovasi, provider'lar, router va service'lar
frontend/      React + TypeScript ilovasi
desktop/       PyWebView launcher va desktop integratsiyasi
scripts/       Build va Windows preflight skriptlari
.github/       CI workflow'lari
nexus-ai/      Avvalgi mustaqil UI prototipi; integratsiyalashgan ilova emas
~~~

## Hujjatlarni yuritish tartibi

Loyihada ikkita README va bitta xronologik rivojlanish jurnali ishlatiladi:

- README.md — loyihaning asosiy tavsifi va hozirgi holati.
- README.uz.md — shu hujjatning o‘zbekcha nusxasi.
- DEVELOPMENT_LOG.md — sana bo‘yicha qarorlar, bajarilgan ishlar, jarayondagi vazifalar va keyingi qadamlar.

Har bir muhim o‘zgarishdan keyin:
1. O‘zgarishni amalga oshirish va tekshirish.
2. Hozirgi holat, arxitektura, ishga tushirish yoki roadmap o‘zgargan bo‘lsa, ikkala README'ni yangilash.
3. DEVELOPMENT_LOG.md ga sana bilan yangi yozuv qo‘shish.
4. Bajarilgan, jarayondagi va rejalashtirilgan ishlarni alohida saqlash.

README loyihaning **hozirgi tekshirilgan holatini**, development log esa **shu holatga qanday kelib qolinganini** saqlaydi.
