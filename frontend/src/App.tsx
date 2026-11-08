import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  Activity, Bot, Boxes, BookOpen, BriefcaseBusiness, ChevronDown, CircleHelp,
  Command, Cpu, Database, ExternalLink, Gauge, LayoutDashboard, MessageSquare,
  Moon, Network, Plus, RefreshCw, Search, Settings, ShieldCheck, Sun, Workflow, X,
} from "lucide-react";
import { BrowserRouter, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./services/api";
import type { KaggleNotebook } from "./types/kaggle";
import type { OllamaModel, OllamaStatus } from "./types/ollama";

type Theme = "dark" | "light";

function formatBytes(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes)) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return value.toFixed(value >= 10 || unit === 0 ? 0 : 1) + " " + units[unit];
}

function Shell({
  title,
  environment,
  theme,
  onThemeChange,
  refreshing,
  onRefresh,
  children,
}: {
  title: string;
  environment: string;
  theme: Theme;
  onThemeChange: () => void;
  refreshing?: boolean;
  onRefresh?: () => void;
  children: ReactNode;
}) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
      if (event.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const commands = [
    { label: "Dashboard", detail: "Overview and runtime", path: "/" },
    { label: "Notebooks", detail: "Kaggle notebook library", path: "/notebooks" },
    { label: "Portfolio", detail: "Your AI projects", path: "/portfolio" },
  ].filter((item) => (item.label + " " + item.detail).toLowerCase().includes(paletteQuery.toLowerCase()));

  const goTo = (path: string) => {
    navigate(path);
    setPaletteOpen(false);
    setPaletteQuery("");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" end className="brand">
          <span className="brand-mark"><Command size={19} strokeWidth={2.2} /></span>
          <span className="brand-copy"><strong>NEXUS</strong><small>AI WORKSPACE</small></span>
        </NavLink>

        <button className="workspace-switcher" type="button">
          <span className="workspace-avatar">N</span>
          <span className="workspace-copy"><strong>Personal workspace</strong><small>Local environment</small></span>
          <ChevronDown size={15} />
        </button>

        <div className="nav-group">
          <p className="nav-label">WORKSPACE</p>
          <NavLink to="/" end className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}><LayoutDashboard size={17} />Dashboard</NavLink>
          <a className="nav-item" href="/#conversations"><MessageSquare size={17} />Conversations</a>
          <a className="nav-item" href="/#agents"><Bot size={17} />My Agents</a>
          <a className="nav-item" href="/#workflows"><Workflow size={17} />Workflows</a>
          <NavLink to="/portfolio" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}><BriefcaseBusiness size={17} />Portfolio</NavLink>
        </div>

        <div className="nav-group">
          <p className="nav-label">RESOURCES</p>
          <a className="nav-item" href="/#models"><Boxes size={17} />Models</a>
          <NavLink to="/notebooks" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}><BookOpen size={17} />Notebooks</NavLink>
          <a className="nav-item" href="/#knowledge"><Database size={17} />Knowledge Base</a>
          <a className="nav-item" href="/#integrations"><Network size={17} />Integrations</a>
        </div>

        <div className="nav-group">
          <p className="nav-label">SYSTEM</p>
          <a className="nav-item" href="/#runtime"><Activity size={17} />Runtime Monitor</a>
          <a className="nav-item" href="/#settings"><Settings size={17} />Settings</a>
        </div>

        <div className="sidebar-bottom">
          <div className="local-card">
            <span className="local-card-icon"><ShieldCheck size={16} /></span>
            <span><strong>Local-first</strong><small>Your data stays on device</small></span>
          </div>
          <div className="profile-row">
            <span className="profile-avatar">U</span>
            <span className="profile-copy"><strong>Local User</strong><small>Administrator</small></span>
            <button className="icon-button small" type="button" aria-label="Help"><CircleHelp size={17} /></button>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>{title}</strong></div>
          <div className="topbar-actions">
            <span className="environment"><span className="environment-dot" />{environment}</span>
            <button className="icon-button" type="button" onClick={onThemeChange} aria-label="Change theme">{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button>
            {onRefresh && <button className="icon-button" type="button" onClick={onRefresh} aria-label="Refresh data" disabled={refreshing}><RefreshCw size={16} className={refreshing ? "spin" : ""} /></button>}
            <span className="profile-avatar top-avatar">U</span>
          </div>
        </header>
        {children}
      </main>

      {paletteOpen && (
        <div className="command-overlay" role="presentation" onMouseDown={() => setPaletteOpen(false)}>
          <section className="command-palette" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={(event) => event.stopPropagation()}>
            <div className="command-search"><Search size={17} /><input autoFocus value={paletteQuery} onChange={(event) => setPaletteQuery(event.target.value)} placeholder="Search pages and actions..." aria-label="Search commands" /><kbd>ESC</kbd><button type="button" className="icon-button" onClick={() => setPaletteOpen(false)} aria-label="Close"><X size={16} /></button></div>
            <p className="command-label">QUICK NAVIGATION</p>
            {commands.length ? commands.map((item) => <button type="button" className="command-item" key={item.path} onClick={() => goTo(item.path)}><span><strong>{item.label}</strong><small>{item.detail}</small></span><span className="command-enter">↵</span></button>) : <p className="command-empty">No matching pages</p>}
            <div className="command-footer"><span><kbd>CTRL</kbd> + <kbd>K</kbd> to open</span><span>{location.pathname}</span></div>
          </section>
        </div>
      )}
    </div>
  );
}

function DashboardPage({ theme, onThemeChange }: { theme: Theme; onThemeChange: () => void }) {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextStatus = await api.getOllamaStatus();
      setStatus(nextStatus);
      setModels(nextStatus.connected ? await api.getModels() : []);
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Noma’lum xatolik yuz berdi.");
      setStatus({ connected: false, version: null, message: "Backend API bilan aloqa yo‘q." });
      setModels([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const connected = status?.connected === true;

  return (
    <Shell title="Dashboard" environment="LOCAL ENVIRONMENT" theme={theme} onThemeChange={onThemeChange} refreshing={loading} onRefresh={() => void refresh()}>
      <section className="page-content">
        <div className="page-heading">
          <div><p className="eyebrow">OVERVIEW / SYSTEM</p><h1>Dashboard</h1><p className="page-subtitle">Your local AI environment at a glance.</p></div>
          <button className="primary-button" type="button" onClick={() => window.location.hash = "agents"}><Plus size={16} />Create agent</button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="section-heading"><h2>System overview</h2><span className="muted-note">{updatedAt ? "Updated " + updatedAt.toLocaleTimeString() : "Waiting for data"}</span></div>
        <div className="stats-grid">
          <article className="stat-card"><div className="stat-top"><span>Ollama runtime</span><span className="stat-icon"><Activity size={17} /></span></div><div className="stat-value status-value"><span className={"status-dot " + (connected ? "online" : "offline")} />{loading && !status ? "Checking…" : connected ? "Connected" : "Offline"}</div><p className="stat-foot">{status?.version ? "Version " + status.version : "Local model runtime"}</p></article>
          <article className="stat-card"><div className="stat-top"><span>Installed models</span><span className="stat-icon"><Boxes size={17} /></span></div><div className="stat-value">{models.length}</div><p className="stat-foot">Available in local Ollama</p></article>
          <article className="stat-card"><div className="stat-top"><span>AI agents</span><span className="stat-icon"><Bot size={17} /></span></div><div className="stat-value">—</div><p className="stat-foot">Agent workspace coming next</p></article>
          <article className="stat-card"><div className="stat-top"><span>Workflows</span><span className="stat-icon"><Workflow size={17} /></span></div><div className="stat-value">—</div><p className="stat-foot">Automation pipeline</p></article>
        </div>

        <div className="content-grid">
          <section className="panel models-panel" id="models">
            <div className="panel-header"><div><h2>Installed models</h2><p>Models available on this machine</p></div><button className="text-button" type="button" onClick={() => void refresh()}>Refresh <RefreshCw size={13} /></button></div>
            {!connected ? (
              <div className="diagnostic-state">
                <div className="diagnostic-icon"><Cpu size={21} /></div>
                <div className="diagnostic-copy"><span className="diagnostic-status"><i />RUNTIME OFFLINE</span><strong>Ollama is not responding yet</strong><p>Start the Ollama service on this device, then check the connection again. Your workspace is ready when the local API becomes available.</p><code>127.0.0.1:11434</code></div>
                <button className="secondary-button" type="button" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} className={loading ? "spin" : ""} />Check connection</button>
              </div>
            ) : models.length === 0 ? (
              <div className="empty-state"><div className="empty-icon"><Boxes size={22} /></div><strong>No models found</strong><p>Pull a model using Ollama to see it listed here.</p><code>ollama pull llama3.2</code></div>
            ) : (
              <div className="model-list">{models.map((model) => <div className="model-row" key={model.digest ?? model.name}><div className="model-symbol"><Cpu size={17} /></div><div className="model-info"><strong>{model.name}</strong><span>{[model.family, model.parameter_size, model.quantization_level].filter(Boolean).join(" · ") || "Local model"}</span></div><span className="model-size">{formatBytes(model.size)}</span><span className="model-ready"><span className="status-dot online" />Ready</span></div>)}</div>
            )}
            <div className="panel-footer"><span>{models.length} model{models.length === 1 ? "" : "s"} detected</span><span>Powered by Ollama</span></div>
          </section>

          <section className="panel runtime-panel" id="runtime">
            <div className="panel-header"><div><h2>Runtime diagnostics</h2><p>Local inference service</p></div><Gauge size={18} className="panel-muted-icon" /></div>
            <div className="runtime-status"><div className={"runtime-indicator " + (connected ? "is-online" : "")}><span /></div><div><strong>{connected ? "Runtime operational" : "Waiting for Ollama"}</strong><p>{status?.message ?? "Checking connection…"}</p></div></div>
            <div className="detail-row"><span>Service</span><strong>Ollama</strong></div>
            <div className="detail-row"><span>Endpoint</span><code>127.0.0.1:11434</code></div>
            <div className="detail-row"><span>API gateway</span><code>127.0.0.1:8000</code></div>
            <div className="runtime-hint"><ShieldCheck size={15} /><span>Requests are routed through the local NEXUS API.</span></div>
          </section>
        </div>
        <div className="bottom-note"><span className="note-mark">N</span><span>NEXUS AI <b>0.3.0</b></span><span className="note-separator">·</span><span>Local-first intelligence workspace</span></div>
      </section>
    </Shell>
  );
}

function NotebooksPage({ theme, onThemeChange }: { theme: Theme; onThemeChange: () => void }) {
  const [notebooks, setNotebooks] = useState<KaggleNotebook[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pulling, setPulling] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNotebooks = useCallback(async (search = query) => {
    setLoading(true);
    setError(null);
    try {
      setNotebooks(await api.getKaggleNotebooks(search || undefined));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebooklarni yuklab bo‘lmadi.");
      setNotebooks([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => { void loadNotebooks(""); }, []);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void loadNotebooks(query);
  };

  const pullNotebook = async (notebook: KaggleNotebook) => {
    const [owner, slug] = notebook.ref.split("/");
    if (!owner || !slug) return;
    setPulling(notebook.ref);
    setNotice(null);
    try {
      const result = await api.pullKaggleNotebook(owner, slug);
      setNotice("Downloaded " + result.filename + " to backend/data/kaggle.");
      setNotebooks((current) => current.map((item) => item.ref === notebook.ref ? { ...item, is_pulled: true } : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notebookni yuklab bo‘lmadi.");
    } finally {
      setPulling(null);
    }
  };

  const formatDate = (value: string | null) => {
    if (!value) return "Update date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
  };

  return (
    <Shell title="Notebooks" environment="KAGGLE LIBRARY" theme={theme} onThemeChange={onThemeChange}>
      <section className="page-content notebooks-page">
        <div className="page-heading"><div><p className="eyebrow">RESOURCES / KAGGLE</p><h1>Notebooks</h1><p className="page-subtitle">Explore and pull your Kaggle notebooks into the NEXUS workspace.</p></div><a className="primary-button" href="https://www.kaggle.com/code" target="_blank" rel="noreferrer">Explore Kaggle <ExternalLink size={14} /></a></div>
        <form className="notebook-search" onSubmit={handleSearch}><Search size={18} /><input aria-label="Search Kaggle notebooks" placeholder="Search notebooks by title or topic..." value={query} onChange={(event) => setQuery(event.target.value)} /><button type="submit" disabled={loading}>Search</button></form>
        {notice && <div className="success-banner">{notice}</div>}
        {error && <div className="error-banner">{error}<span> Check Kaggle credentials in backend/.env and confirm the Kaggle CLI is installed.</span></div>}
        <div className="section-heading notebook-results-heading"><h2>Notebook library</h2><span className="muted-note">{loading ? "Loading…" : notebooks.length + " results"}</span></div>
        {loading ? (
          <div className="notebook-grid">{[1, 2, 3].map((item) => <div className="notebook-card skeleton-card" key={item}><div className="skeleton-line wide" /><div className="skeleton-line medium" /><div className="skeleton-line short" /><div className="skeleton-footer" /></div>)}</div>
        ) : notebooks.length === 0 && !error ? (
          <div className="empty-state notebook-empty"><div className="empty-icon"><BookOpen size={22} /></div><strong>No notebooks found</strong><p>Try another search, or check that your Kaggle account has notebooks available.</p></div>
        ) : (
          <div className="notebook-grid">{notebooks.map((notebook) => (
            <article className="notebook-card" key={notebook.ref}>
              <div className="notebook-card-top"><span className="kaggle-mark">K</span><span className="notebook-language">{notebook.language || "Notebook"}</span></div>
              <h3>{notebook.title}</h3><p className="notebook-ref">{notebook.ref}</p>
              <div className="notebook-meta"><span><span className="meta-symbol">↑</span>{notebook.votes.toLocaleString()} votes</span><span>{formatDate(notebook.last_updated)}</span></div>
              <div className="notebook-actions"><a className="notebook-open" href={notebook.url} target="_blank" rel="noreferrer">Open on Kaggle <ExternalLink size={13} /></a><button className="notebook-pull" type="button" onClick={() => void pullNotebook(notebook)} disabled={pulling === notebook.ref || notebook.is_pulled}>{notebook.is_pulled ? "Downloaded" : pulling === notebook.ref ? "Pulling…" : "Pull .ipynb"}</button></div>
            </article>
          ))}</div>
        )}
        <div className="bottom-note"><span className="note-mark">N</span><span>NEXUS AI <b>0.3.0</b></span><span className="note-separator">·</span><span>Notebook metadata provided by Kaggle</span></div>
      </section>
    </Shell>
  );
}

function PortfolioPage({ theme, onThemeChange }: { theme: Theme; onThemeChange: () => void }) {
  return (
    <Shell title="Portfolio" environment="PROJECT SPACE" theme={theme} onThemeChange={onThemeChange}>
      <section className="page-content portfolio-page">
        <div className="page-heading"><div><p className="eyebrow">WORKSPACE / SHOWCASE</p><h1>Portfolio</h1><p className="page-subtitle">A home for the AI projects you build with NEXUS.</p></div></div>
        <section className="panel portfolio-empty">
          <div className="portfolio-orbit"><span /><span /><span /><BriefcaseBusiness size={25} /></div>
          <p className="eyebrow">YOUR PROJECT SPACE</p>
          <h2>Your work will live here</h2>
          <p>Projects, agents, workflows and notebook-based experiments can be gathered here as a clear, shareable portfolio. The portfolio data and publishing flow are not connected yet.</p>
          <span className="portfolio-status"><i />PORTFOLIO FOUNDATION</span>
        </section>
      </section>
    </Shell>
  );
}

function App() {
  const [theme, setTheme] = useState<Theme>("dark");
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  const onThemeChange = () => setTheme((current) => current === "dark" ? "light" : "dark");

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/notebooks" element={<NotebooksPage theme={theme} onThemeChange={onThemeChange} />} />
        <Route path="/portfolio" element={<PortfolioPage theme={theme} onThemeChange={onThemeChange} />} />
        <Route path="*" element={<DashboardPage theme={theme} onThemeChange={onThemeChange} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
