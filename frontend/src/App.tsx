import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, Bot, Boxes, ChevronDown, CircleHelp, Command, Cpu,
  Database, Gauge, LayoutDashboard, MessageSquare, Moon, Network,
  Plus, RefreshCw, Settings, ShieldCheck, Sun, Volume2, VolumeX, Workflow,
} from "lucide-react";
import KagglePanel from "./components/KagglePanel";
import { api } from "./services/api";
import type { OllamaModel, OllamaStatus } from "./types/ollama";
import "./kaggle-styles.css";

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
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function App() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const refreshing = useRef(false);

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
      const nextStatus = await api.getOllamaStatus();
      setStatus(nextStatus);
      if (nextStatus.connected) {
        setModels(await api.getModels());
      } else {
        setModels([]);
      }
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Noma’lum xatolik yuz berdi.");
      setStatus({ connected: false, version: null, mode: "local", message: "Backend API bilan aloqa yo‘q." });
      setModels([]);
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

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const connected = status?.connected === true;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Command size={19} strokeWidth={2.2} /></div>
          <div><strong>NEXUS</strong><span>AI PLATFORM</span></div>
        </div>

        <button className="workspace-switcher">
          <span className="workspace-avatar">N</span>
          <span className="workspace-copy"><strong>Personal workspace</strong><small>Local environment</small></span>
          <ChevronDown size={15} />
        </button>

        <div className="nav-group">
          <p className="nav-label">WORKSPACE</p>
          <a className="nav-item active" href="#dashboard"><LayoutDashboard size={17} />Dashboard</a>
          <a className="nav-item" href="#conversations"><MessageSquare size={17} />Conversations</a>
          <a className="nav-item" href="#agents"><Bot size={17} />My Agents</a>
          <a className="nav-item" href="#workflows"><Workflow size={17} />Workflows</a>
        </div>

        <div className="nav-group">
          <p className="nav-label">RESOURCES</p>
          <a className="nav-item" href="#models"><Boxes size={17} />Models<span className="nav-count">{models.length}</span></a>
          <a className="nav-item" href="#knowledge"><Database size={17} />Knowledge Base</a>
          <a className="nav-item" href="#integrations"><Network size={17} />Integrations</a>
        </div>

        <div className="nav-group">
          <p className="nav-label">SYSTEM</p>
          <a className="nav-item" href="#runtime"><Activity size={17} />Runtime Monitor</a>
          <a className="nav-item" href="#settings"><Settings size={17} />Settings</a>
        </div>

        <div className="sidebar-bottom">
          <div className="local-card">
            <div className="local-card-icon"><ShieldCheck size={16} /></div>
            <div><strong>Local-first</strong><span>Your data stays on device</span></div>
          </div>
          <div className="profile-row">
            <div className="profile-avatar">U</div>
            <div className="profile-copy"><strong>Local User</strong><span>Administrator</span></div>
            <button className="icon-button small" aria-label="Help"><CircleHelp size={17} /></button>
          </div>
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>Dashboard</strong></div>
          <div className="topbar-actions">
            <div className="environment"><span className="environment-dot" />LOCAL ENVIRONMENT</div>
            <button className="icon-button" onClick={() => { setTheme(theme === "dark" ? "light" : "dark"); playUiSound(740); }} aria-label="Change theme" title="Change theme">
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button className="icon-button" onClick={() => { playUiSound(520); void refresh(); }} aria-label="Refresh data" title="Refresh data" disabled={loading}>
              <RefreshCw size={16} className={loading ? "spin" : ""} />
            </button>
            <button className="icon-button" onClick={() => setSoundEnabled((enabled) => !enabled)} aria-label={soundEnabled ? "Disable sound effects" : "Enable sound effects"} title={soundEnabled ? "Sound effects on" : "Sound effects off"} aria-pressed={soundEnabled}>{soundEnabled ? <Volume2 size={17} /> : <VolumeX size={17} />}</button>
            <div className="profile-avatar top-avatar">U</div>
          </div>
        </header>

        <section className="page-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">OVERVIEW</p>
              <h1>Dashboard</h1>
              <p className="page-subtitle">Your local AI environment at a glance.</p>
            </div>
            <button className="primary-button" onClick={() => window.location.hash = "agents"}><Plus size={16} />Create agent</button>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <div className="section-heading">
            <h2>System overview</h2>
            <span className="muted-note">{updatedAt ? `Updated ${updatedAt.toLocaleTimeString()}` : "Waiting for data"}</span>
          </div>

          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-top"><span>Ollama runtime</span><div className="stat-icon"><Activity size={17} /></div></div>
              <div className="stat-value status-value"><span className={`status-dot ${connected ? "online" : "offline"}`} />{loading && !status ? "Checking…" : connected ? "Connected" : "Offline"}</div>
              <p className="stat-foot">{status?.version ? `Version ${status.version}` : "Local model runtime"}</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>Installed models</span><div className="stat-icon"><Boxes size={17} /></div></div>
              <div className="stat-value">{models.length}</div>
              <p className="stat-foot">{status?.mode === "kaggle" ? "Available in Kaggle Ollama" : "Available in local Ollama"}</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>AI agents</span><div className="stat-icon"><Bot size={17} /></div></div>
              <div className="stat-value">—</div>
              <p className="stat-foot">Agent workspace coming next</p>
            </article>
            <article className="stat-card">
              <div className="stat-top"><span>Workflows</span><div className="stat-icon"><Workflow size={17} /></div></div>
              <div className="stat-value">—</div>
              <p className="stat-foot">Automation pipeline</p>
            </article>
          </div>

          <div className="content-grid">
            <section className="panel models-panel" id="models">
              <div className="panel-header">
                <div><h2>Installed models</h2><p>Models available on this machine</p></div>
                <button className="text-button" onClick={() => void refresh()}>Refresh <RefreshCw size={13} /></button>
              </div>
              {!connected ? (
                <div className="empty-state">
                  <div className="empty-icon"><Cpu size={22} /></div>
                  <strong>Ollama is not connected</strong>
                  <p>Start Ollama and make sure its local API is available at <code>127.0.0.1:11434</code>.</p>
                </div>
              ) : models.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon"><Boxes size={22} /></div>
                  <strong>No models found</strong>
                  <p>Pull a model using Ollama to see it listed here.</p>
                  <code>ollama pull llama3.2</code>
                </div>
              ) : (
                <div className="model-list">
                  {models.map((model) => (
                    <div className="model-row" key={model.digest ?? model.name}>
                      <div className="model-symbol"><Cpu size={17} /></div>
                      <div className="model-info"><strong>{model.name}</strong><span>{[model.family, model.parameter_size, model.quantization_level].filter(Boolean).join(" · ") || "Local model"}</span></div>
                      <span className="model-size">{formatBytes(model.size)}</span>
                      <span className="model-ready"><span className="status-dot online" />Ready</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="panel-footer"><span>{models.length} model{models.length === 1 ? "" : "s"} detected</span><span>Powered by Ollama</span></div>
            </section>

            <section className="panel runtime-panel" id="runtime">
              <div className="panel-header"><div><h2>Runtime connection</h2><p>{status?.mode === "kaggle" ? "Kaggle inference service" : "Local inference service"}</p></div><Gauge size={18} className="panel-muted-icon" /></div>
              <div className="runtime-status">
                <div className={`runtime-indicator ${connected ? "is-online" : ""}`}><span /></div>
                <div><strong>{connected ? "Runtime operational" : "Runtime unavailable"}</strong><p>{status?.message ?? "Checking connection…"}</p></div>
              </div>
              <div className="detail-row"><span>Service</span><strong>Ollama</strong></div>
              <div className="detail-row"><span>Selected runtime</span><code>{status?.mode === "kaggle" ? "Kaggle GPU" : "127.0.0.1:11434"}</code></div>
              <div className="detail-row"><span>API gateway</span><code>127.0.0.1:8000</code></div>
              <div className="runtime-hint"><ShieldCheck size={15} /><span>Requests are routed through the local NEXUS API.</span></div>
            </section>
          </div>

          <div className="kaggle-section">
            <KagglePanel onModeChange={() => void refresh()} />
          </div>

          <div className="bottom-note"><span className="note-mark">N</span><span>NEXUS AI <b>0.1.0</b></span><span className="note-separator">·</span><span>Local-first intelligence workspace</span></div>
        </section>
      </main>
    </div>
  );
}

export default App;
