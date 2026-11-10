import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, Bot, Boxes, Briefcase, ChevronDown, CircleHelp, Command,
  Database, Gauge, LayoutDashboard, MessageSquare, Moon, Network,
  Plus, RefreshCw, HardDrive, Search, Settings, ShieldCheck, Sun, Volume2, VolumeX, Workflow,
} from "lucide-react";
import KagglePanel from "./components/KagglePanel";
import WorkspacePanel from "./components/WorkspacePanel";
import ChatPanel from "./components/ChatPanel";
import AgentPanel from "./components/AgentPanel";
import ModelsPanel from "./components/ModelsPanel";
import ProviderPanel from "./components/ProviderPanel";
import SettingsPanel from "./components/SettingsPanel";
import { api } from "./services/api";
import type { OllamaModel, OllamaStatus } from "./types/ollama";
import type { KaggleStatus } from "./types/kaggle";
import { useTranslation } from "./i18n";
import { AgentProvider } from "./contexts/AgentContext";
import "./providers-styles.css";

type Theme = "dark" | "light";
type View = "dashboard" | "explorer" | "chat" | "agents" | "providers" | "settings" | "portfolio";

const viewFromHash = (hash: string): View | null => {
  switch (hash.replace(/^#/, "")) {
    case "dashboard": return "dashboard";
    case "explorer": return "explorer";
    case "conversations": return "chat";
    case "agents": return "agents";
    case "providers": return "providers";
    case "settings": return "settings";
    case "portfolio": return "portfolio";
    default: return null;
  }
};

const hashForView = (view: View): string => ({
  dashboard: "#dashboard",
  explorer: "#explorer",
  chat: "#conversations",
  agents: "#agents",
  providers: "#providers",
  settings: "#settings",
  portfolio: "#portfolio",
})[view];

function App() {
  const { t, language, setLanguage } = useTranslation();
  const [theme, setTheme] = useState<Theme>("dark");
  const [activeView, setActiveView] = useState<View>("dashboard");
  const [visitedViews, setVisitedViews] = useState<Set<View>>(() => new Set(["dashboard"]));
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const navigateTo = useCallback((view: View) => {
    setActiveView(view);
    setVisitedViews((current) => current.has(view) ? current : new Set(current).add(view));
    const nextHash = hashForView(view);
    if (window.location.hash !== nextHash) {
      window.history.pushState(null, "", nextHash);
    }
  }, []);

  useEffect(() => {
    const syncViewFromLocation = () => {
      const view = viewFromHash(window.location.hash);
      if (!view) {
        window.history.replaceState(null, "", hashForView("dashboard"));
        setActiveView("dashboard");
        setVisitedViews((current) => current.has("dashboard") ? current : new Set(current).add("dashboard"));
        return;
      }
      setActiveView(view);
      setVisitedViews((current) => current.has(view) ? current : new Set(current).add(view));
    };

    syncViewFromLocation();
    window.addEventListener("popstate", syncViewFromLocation);
    window.addEventListener("hashchange", syncViewFromLocation);
    return () => {
      window.removeEventListener("popstate", syncViewFromLocation);
      window.removeEventListener("hashchange", syncViewFromLocation);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        setPaletteQuery("");
      }
      if (event.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [kaggleStatus, setKaggleStatus] = useState<KaggleStatus | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [providerModels, setProviderModels] = useState<OllamaModel[]>([]);
  const [activeProvider, setActiveProvider] = useState("ollama");
  const [providerConnected, setProviderConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [preferencesReady, setPreferencesReady] = useState(false);
  const refreshing = useRef(false);
  const kaggleRefreshing = useRef(false);

  const playUiSound = useCallback((frequency = 660) => {
    if (!soundEnabled || typeof window === "undefined") return;
    try {
      const AudioContextClass = window.AudioContext;
      if (!AudioContextClass) return;
      const context = new AudioContextClass();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, context.currentTime);
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.035, context.currentTime + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.09);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.1);
      oscillator.onended = () => void context.close();
    } catch {
      // Audio feedback is optional; UI actions must work without it.
    }
  }, [soundEnabled]);

  const refresh = useCallback(async (silent = false) => {
    if (refreshing.current) return;
    refreshing.current = true;
    if (!silent) setLoading(true);
    setError(null);
    try {
      const [nextStatus, catalog] = await Promise.all([
        api.getOllamaStatus(),
        api.getProviderCatalog(),
      ]);
      setStatus(nextStatus);
      const nextModels = nextStatus.connected ? await api.getModels() : [];
      setModels(nextModels);
      setActiveProvider(catalog.active_provider);
      const selected = catalog.providers.find((provider) => provider.id === catalog.active_provider);
      setProviderConnected(Boolean(selected?.connected));
      setProviderModels((selected?.models ?? []).map((item) => ({
        name: item.name,
        size: typeof item.metadata.size === "number" ? item.metadata.size : null,
        modified_at: typeof item.metadata.modified_at === "string" ? item.metadata.modified_at : null,
        digest: typeof item.metadata.digest === "string" ? item.metadata.digest : null,
        family: typeof item.metadata.family === "string" ? item.metadata.family : null,
        parameter_size: typeof item.metadata.parameter_size === "string" ? item.metadata.parameter_size : null,
        quantization_level: typeof item.metadata.quantization_level === "string" ? item.metadata.quantization_level : null,
      })));
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("status.unknownError"));
      setStatus({ connected: false, version: null, mode: "local", message: t("status.backendUnavailable") });
      setModels([]);
      setProviderModels([]);
      setProviderConnected(false);
    } finally {
      refreshing.current = false;
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh(true);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const refreshKaggle = useCallback(async () => {
    if (kaggleRefreshing.current) return;
    kaggleRefreshing.current = true;
    try { setKaggleStatus(await api.getKaggleStatus()); }
    catch { /* Kaggle is optional; keep the last known state when unavailable. */ }
    finally { kaggleRefreshing.current = false; }
  }, []);

  useEffect(() => {
    if (activeView === "dashboard") void refreshKaggle();
  }, [activeView, refreshKaggle]);

  useEffect(() => {
    if (activeView !== "dashboard" || !kaggleStatus || !["pushing", "queued", "starting"].includes(kaggleStatus.state)) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshKaggle();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [activeView, kaggleStatus?.state, refreshKaggle]);

  useEffect(() => {
    let active = true;
    void api.getPreferences()
      .then((preferences) => {
        if (!active) return;
        setTheme(preferences.theme);
        setSoundEnabled(preferences.sound_enabled);
        setLanguage(preferences.language ?? "uz");
      })
      .catch(() => {
        // Keep safe local defaults when the preferences endpoint is unavailable.
      })
      .finally(() => {
        if (active) setPreferencesReady(true);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = language;
  }, [theme, language]);

  useEffect(() => {
    if (!preferencesReady) return;
    const timer = window.setTimeout(() => {
      void api.savePreferences({ theme, sound_enabled: soundEnabled, language })
        .catch((err: unknown) => {
          setError(err instanceof Error ? `${t("settings.preferencesSaveError")}: ${err.message}` : t("settings.preferencesSaveError"));
        });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [theme, soundEnabled, language, preferencesReady]);

  const connected = providerConnected;
  const ollamaConnected = status?.connected === true;
  const commands: { view: View; label: string; detail: string }[] = [
    { view: "dashboard", label: t("nav.dashboard"), detail: t("commands.dashboardDetail") },
    { view: "explorer", label: t("nav.explorer"), detail: t("commands.explorerDetail") },
    { view: "chat", label: t("nav.conversations"), detail: t("commands.chatDetail") },
    { view: "agents", label: t("nav.agents"), detail: t("commands.agentsDetail") },
    { view: "providers", label: t("nav.providers"), detail: t("commands.providersDetail") },
    { view: "settings", label: t("nav.settings"), detail: t("commands.settingsDetail") },
    { view: "portfolio", label: t("nav.portfolio"), detail: t("commands.portfolioDetail") },
  ];
  const filteredCommands = commands.filter((item) =>
    (item.label + " " + item.detail).toLowerCase().includes(paletteQuery.trim().toLowerCase())
  );
  const openCommand = (view: View) => {
    navigateTo(view);
    setPaletteOpen(false);
    setPaletteQuery("");
  };

  return (
    <AgentProvider>
    <div className="app-shell">
      <a className="skip-link" href="#main-content">{t("accessibility.skipToContent")}</a>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Command size={19} strokeWidth={2.2} /></div>
          <div><strong>NEXUS</strong><span>AI PLATFORM</span></div>
        </div>

        <button className="workspace-switcher">
          <span className="workspace-avatar">N</span>
          <span className="workspace-copy"><strong>{t("workspace.personal")}</strong><small>{t("workspace.local")}</small></span>
          <ChevronDown size={15} />
        </button>

        <nav className="sidebar-nav" aria-label={t("nav.workspaceTitle")}>
        <div className="nav-group">
          <p className="nav-label">{t("nav.workspace")}</p>
          <a className={`nav-item ${activeView === "dashboard" ? "active" : ""}`} href="#dashboard" aria-label={t("nav.dashboard")} title={t("nav.dashboard")} aria-current={activeView === "dashboard" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("dashboard"); }}><LayoutDashboard size={17} aria-hidden="true" />{t("nav.dashboard")}</a>
          <a className={`nav-item ${activeView === "explorer" ? "active" : ""}`} href="#explorer" aria-label={t("nav.explorer")} title={t("nav.explorer")} aria-current={activeView === "explorer" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("explorer"); }}><HardDrive size={17} aria-hidden="true" />{t("nav.explorer")}</a>
          <a className={`nav-item ${activeView === "chat" ? "active" : ""}`} href="#conversations" aria-label={t("nav.conversations")} title={t("nav.conversations")} aria-current={activeView === "chat" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("chat"); }}><MessageSquare size={17} aria-hidden="true" />{t("nav.conversations")}</a>
          <a className={`nav-item ${activeView === "agents" ? "active" : ""}`} href="#agents" aria-label={t("nav.agents")} title={t("nav.agents")} aria-current={activeView === "agents" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("agents"); }}><Bot size={17} aria-hidden="true" />{t("nav.agents")}</a>
          <a className={`nav-item ${activeView === "portfolio" ? "active" : ""}`} href="#portfolio" aria-label={t("nav.portfolio")} title={t("nav.portfolio")} aria-current={activeView === "portfolio" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("portfolio"); }}><Briefcase size={17} aria-hidden="true" />{t("nav.portfolio")}</a>
          <span className="nav-item nav-item-disabled" aria-disabled="true" aria-label={t("nav.workflows")} title={t("nav.workflows")}><Workflow size={17} aria-hidden="true" />{t("nav.workflows")}</span>
        </div>

        <div className="nav-group">
          <p className="nav-label">{t("nav.resources")}</p>
          <span className="nav-item nav-item-disabled" aria-disabled="true" aria-label={t("nav.models")} title={t("nav.models")}><Boxes size={17} aria-hidden="true" />{t("nav.models")}<span className="nav-count">{models.length}</span></span>
          <span className="nav-item nav-item-disabled" aria-disabled="true" aria-label={t("nav.knowledge")} title={t("nav.knowledge")}><Database size={17} aria-hidden="true" />{t("nav.knowledge")}</span>
          <a className={`nav-item ${activeView === "providers" ? "active" : ""}`} href="#providers" aria-label={t("nav.providers")} title={t("nav.providers")} aria-current={activeView === "providers" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("providers"); }}><Network size={17} aria-hidden="true" />{t("nav.providers")}</a>
          <span className="nav-item nav-item-disabled" aria-disabled="true" aria-label={t("nav.integrations")} title={t("nav.integrations")}><Workflow size={17} aria-hidden="true" />{t("nav.integrations")}</span>
        </div>

        <div className="nav-group">
          <p className="nav-label">{t("nav.system")}</p>
          <span className="nav-item nav-item-disabled" aria-disabled="true" aria-label={t("nav.runtime")} title={t("nav.runtime")}><Activity size={17} aria-hidden="true" />{t("nav.runtime")}</span>
          <a className={`nav-item ${activeView === "settings" ? "active" : ""}`} href="#settings" aria-label={t("nav.settings")} title={t("nav.settings")} aria-current={activeView === "settings" ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigateTo("settings"); }}><Settings size={17} aria-hidden="true" />{t("nav.settings")}</a>
        </div>

        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div className="local-card-icon"><ShieldCheck size={16} /></div>
            <div><strong>{t("workspace.localFirst")}</strong><span>{t("workspace.dataLocal")}</span></div>
          </div>
          <div className="profile-row">
            <div className="profile-avatar">U</div>
            <div className="profile-copy"><strong>{t("workspace.localUser")}</strong><span>{t("workspace.admin")}</span></div>
            <button className="icon-button small" aria-label="Help"><CircleHelp size={17} /></button>
          </div>
        </div>
      </aside>

      <main className="main-content" id="main-content" tabIndex={-1}>
        <header className="topbar">
          <div className="breadcrumbs"><span>{t("nav.workspaceTitle")}</span><span className="crumb-separator">/</span><strong>{activeView === "dashboard" ? t("nav.dashboard") : activeView === "explorer" ? t("nav.explorer") : activeView === "agents" ? t("nav.agentRuntime") : activeView === "providers" ? t("nav.providers") : activeView === "settings" ? t("nav.settings") : activeView === "portfolio" ? t("nav.portfolio") : t("nav.aiChat")}</strong></div>
          <div className="topbar-actions">
            <button className="command-trigger" type="button" onClick={() => { setPaletteOpen(true); setPaletteQuery(""); }} aria-label={t("actions.openCommands")} aria-keyshortcuts="Control+K Meta+K" title={t("actions.openCommands")}><Search size={15} /><span>{t("commands.open")}</span><kbd>Ctrl K</kbd></button>
            <label className="language-switch" aria-label={t("actions.language")}><span>{t("actions.language")}</span><select value={language} onChange={(event) => setLanguage(event.target.value as "uz" | "en")}><option value="uz">O‘zbekcha</option><option value="en">English</option></select></label>
            <div className="environment"><span className="environment-dot" />{t("workspace.environment")}</div>
            <button className="icon-button" onClick={() => { setTheme(theme === "dark" ? "light" : "dark"); playUiSound(740); }} disabled={!preferencesReady} aria-label={t("actions.changeTheme")} title={t("actions.changeTheme")}>
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button className="icon-button" onClick={() => { playUiSound(520); void refresh(); }} aria-label={t("actions.refresh")} title={t("actions.refresh")} disabled={loading}>
              <RefreshCw size={16} className={loading ? "spin" : ""} />
            </button>
            <button className="icon-button" onClick={() => setSoundEnabled((enabled) => !enabled)} disabled={!preferencesReady} aria-label={soundEnabled ? t("actions.soundOff") : t("actions.soundOn")} title={soundEnabled ? t("actions.soundOn") : t("actions.soundOff")} aria-pressed={soundEnabled}>{soundEnabled ? <Volume2 size={17} /> : <VolumeX size={17} />}</button>
            <div className="profile-avatar top-avatar">U</div>
          </div>
        </header>

        {visitedViews.has("dashboard") && <div hidden={activeView !== "dashboard"} style={{ display: activeView === "dashboard" ? "block" : "none" }}>
        <section className="page-content" id="dashboard">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{t("dashboard.overview")}</p>
              <h1>{t("nav.dashboard")}</h1>
              <p className="page-subtitle">{t("dashboard.subtitle")}</p>
            </div>
            <button className="primary-button" onClick={() => navigateTo("agents")}><Plus size={16} />{t("dashboard.createAgent")}</button>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <div className="section-heading">
            <h2>{t("dashboard.systemOverview")}</h2>
            <span className="muted-note">{updatedAt ? `${t("dashboard.updated")} ${updatedAt.toLocaleTimeString()}` : t("dashboard.waiting")}</span>
          </div>

          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-top"><span>{t("dashboard.ollamaRuntime")}</span><div className="stat-icon"><Activity size={17} /></div></div>
              <div className="stat-value status-value" aria-live="polite" aria-atomic="true"><span className={`status-dot ${ollamaConnected ? "online" : "offline"}`} />{loading && !status ? t("dashboard.checking") : ollamaConnected ? t("status.connected") : t("status.offline")}</div>
              <p className="stat-foot">{status?.version ? `Version ${status.version}` : t("dashboard.localRuntime")}</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>{t("dashboard.installedModels")}</span><div className="stat-icon"><Boxes size={17} /></div></div>
              <div className="stat-value">{models.length}</div>
              <p className="stat-foot">{status?.mode === "kaggle" ? t("dashboard.kaggleModels") : t("dashboard.localModels")}</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>{t("dashboard.aiAgents")}</span><div className="stat-icon"><Bot size={17} /></div></div>
              <div className="stat-value">—</div>
              <p className="stat-foot">{t("dashboard.agentRuntime")}</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>{t("nav.workflows")}</span><div className="stat-icon"><Workflow size={17} /></div></div>
              <div className="stat-value">—</div>
              <p className="stat-foot">{t("dashboard.automationPipeline")}</p>
            </article>
          </div>

          <div className="content-grid">
            <ModelsPanel models={models} connected={ollamaConnected} onRefresh={() => void refresh(true)} />

            <section className="panel runtime-panel" id="runtime">
              <div className="panel-header"><div><h2>{t("dashboard.runtimeConnection")}</h2><p>{status?.mode === "kaggle" ? t("dashboard.kaggleInference") : t("dashboard.localInference")}</p></div><Gauge size={18} className="panel-muted-icon" /></div>
              <div className="runtime-status">
                <div className={`runtime-indicator ${ollamaConnected ? "is-online" : ""}`}><span /></div>
                <div><strong>{ollamaConnected ? t("dashboard.runtimeOperational") : t("dashboard.runtimeUnavailable")}</strong><p>{status?.message ?? t("dashboard.checkingConnection")}</p></div>
              </div>
              <div className="detail-row"><span>{t("dashboard.service")}</span><strong>Ollama</strong></div>
              <div className="detail-row"><span>{t("dashboard.selectedRuntime")}</span><code>{status?.mode === "kaggle" ? "Kaggle GPU" : "127.0.0.1:11434"}</code></div>
              <div className="detail-row"><span>{t("dashboard.apiGateway")}</span><code>{window.location.host}</code></div>
              <div className="runtime-hint"><ShieldCheck size={15} /><span>{t("dashboard.routedLocally")}</span></div>
            </section>
          </div>

          <div className="kaggle-section"><KagglePanel status={kaggleStatus} onStatusChange={setKaggleStatus} onModeChange={() => { void refresh(); }} /></div>

          <div className="bottom-note"><span className="note-mark">N</span><span>NEXUS AI <b>0.1.0</b></span><span className="note-separator">·</span><span>{t("dashboard.localFirstWorkspace")}</span></div>
        </section>
        </div>}
        {visitedViews.has("explorer") && <section hidden={activeView !== "explorer"} style={{ display: activeView === "explorer" ? "block" : "none" }} className="page-content workstation-page"><WorkspacePanel /></section>}
        {visitedViews.has("providers") && <section hidden={activeView !== "providers"} style={{ display: activeView === "providers" ? "block" : "none" }} className="page-content workstation-page">
          <ProviderPanel activeProvider={activeProvider} onProviderChange={(providerId) => {
            void api.setActiveProvider(providerId).then((result) => {
              setActiveProvider(result.provider_id);
              void refresh(true);
            }).catch((err: unknown) => {
              setError(err instanceof Error ? err.message : t("providers.selectionError"));
            });
          }} />
        </section>}
        {visitedViews.has("settings") && <section hidden={activeView !== "settings"} style={{ display: activeView === "settings" ? "block" : "none" }} className="page-content workstation-page"><SettingsPanel /></section>}
        {visitedViews.has("agents") && <section hidden={activeView !== "agents"} style={{ display: activeView === "agents" ? "block" : "none" }} className="page-content workstation-page">
          <AgentPanel models={providerModels} connected={connected} providerId={activeProvider} />
        </section>}
        {visitedViews.has("chat") && <section hidden={activeView !== "chat"} style={{ display: activeView === "chat" ? "block" : "none" }} className="page-content workstation-page">
          <ChatPanel models={providerModels} connected={connected} providerId={activeProvider} />
        </section>}
        {visitedViews.has("portfolio") && <section hidden={activeView !== "portfolio"} style={{ display: activeView === "portfolio" ? "block" : "none" }} className="page-content workstation-page portfolio-page">
          <div className="page-heading"><div><p className="eyebrow">{t("portfolio.eyebrow")}</p><h1>{t("portfolio.title")}</h1><p className="page-subtitle">{t("portfolio.subtitle")}</p></div></div>
          <section className="panel portfolio-empty">
            <div className="portfolio-orbit"><Briefcase size={25} aria-hidden="true" /></div>
            <h2>{t("portfolio.emptyTitle")}</h2>
            <p>{t("portfolio.emptyDescription")}</p>
          </section>
        </section>}
      </main>
      {paletteOpen && <div className="command-overlay" onMouseDown={() => setPaletteOpen(false)}>
        <section className="command-palette" role="dialog" aria-modal="true" aria-labelledby="command-palette-title" onMouseDown={(event) => event.stopPropagation()}>
          <div className="command-search"><Search size={17} aria-hidden="true" /><input autoFocus type="search" value={paletteQuery} onChange={(event) => setPaletteQuery(event.target.value)} placeholder={t("commands.placeholder")} aria-label={t("commands.placeholder")} /><kbd>ESC</kbd><button type="button" className="icon-button" onClick={() => setPaletteOpen(false)} aria-label={t("commands.close")}>×</button></div>
          <p className="command-label" id="command-palette-title">{t("commands.title")}</p>
          <div className="command-results">
            {filteredCommands.length ? filteredCommands.map((item) => <button type="button" className="command-item" key={item.view} onClick={() => openCommand(item.view)}><span><strong>{item.label}</strong><small>{item.detail}</small></span><span className="command-enter" aria-hidden="true">↵</span></button>) : <p className="command-empty">{t("commands.empty")}</p>}
          </div>
        </section>
      </div>}
    </div>
    </AgentProvider>
  );
}

export default App;
