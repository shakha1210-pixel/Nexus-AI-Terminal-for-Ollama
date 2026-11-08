import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, ChevronRight, Cloud, Cpu, Network, Save, ShieldCheck, Workflow } from "lucide-react";
import { api } from "../services/api";
import type { FailureKind, ProviderCatalog, ProviderPolicy, SwitchingMode } from "../types/providers";

const DEFAULT_POLICY: ProviderPolicy = {
  mode: "manual_only", max_switches_per_request: 1, allowed_transitions: {},
  exception_allowlist: [], retry_limit: 1, cooldown_seconds: 0, require_confirmation: false,
};
const FAILURE_OPTIONS: { value: FailureKind; label: string }[] = [
  { value: "timeout", label: "Timeout" }, { value: "rate_limit", label: "Rate limit (429)" },
  { value: "server_error", label: "Server error (5xx)" }, { value: "network_error", label: "Network error" },
  { value: "unknown", label: "Unknown exception" },
];
const PROVIDERS = [
  { id: "ollama", name: "Ollama Runtime", detail: "Native Ollama API · local or Kaggle GPU", icon: Cpu, state: "Adapter foundation" },
  { id: "openai-compatible", name: "OpenAI-compatible", detail: "OpenAI /v1-compatible endpoints", icon: Network, state: "Adapter foundation" },
  { id: "anthropic", name: "Anthropic", detail: "Native Messages API", icon: Workflow, state: "Planned" },
  { id: "gemini", name: "Google Gemini", detail: "Native Gemini API", icon: Workflow, state: "Planned" },
];

export default function ProviderPanel({ activeProvider, onProviderChange }: { activeProvider: string; onProviderChange: (providerId: string) => void }) {
  const [policy, setPolicy] = useState<ProviderPolicy>(DEFAULT_POLICY);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [pathText, setPathText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    void api.getProviderPolicy().then((value) => {
      if (!active) return;
      setPolicy(value);
      const transitions = value.allowed_transitions;
      const allTargets = Object.values(transitions).flat();
      const start = Object.keys(transitions).find((source) => !allTargets.includes(source));
      const chain: string[] = [];
      let current = start;
      while (current && !chain.includes(current)) {
        chain.push(current);
        current = transitions[current]?.[0];
      }
      setPathText(chain.join(" → "));
    }).catch((e: unknown) => {
      if (active) setError(e instanceof Error ? e.message : "Policy could not be loaded.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
    void api.getProviderCatalog().then(setCatalog).catch((e: unknown) => {
      if (active) setError(e instanceof Error ? e.message : "Provider catalog could not be loaded.");
    });
  }, []);

  const path = useMemo(() => pathText.split("→").map((part) => part.trim()).filter(Boolean), [pathText]);
  const update = <K extends keyof ProviderPolicy>(key: K, value: ProviderPolicy[K]) => {
    setPolicy((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };

  const save = async () => {
    setSaving(true); setError(null); setSaved(false);
    try {
      const allowed_transitions: Record<string, string[]> = {};
      for (let index = 0; index < path.length - 1; index += 1) {
        allowed_transitions[path[index]] = [path[index + 1]];
      }
      const next = await api.saveProviderPolicy({ ...policy, allowed_transitions });
      setPolicy(next); setSaved(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Policy could not be saved."); }
    finally { setSaving(false); }
  };

  const toggleFailure = (value: FailureKind, checked: boolean) => {
    update("exception_allowlist", checked
      ? [...policy.exception_allowlist, value]
      : policy.exception_allowlist.filter((item) => item !== value));
  };

  return <div className="provider-page">
    <section className="panel provider-panel">
      <div className="panel-header"><div><h2>Provider registry</h2><p>One normalized interface for independent inference backends</p></div><Network size={18} className="panel-muted-icon" /></div>
      <div className="provider-grid">
        {PROVIDERS.map(({ id, name, detail, icon: Icon, state }) => {
          const live = catalog?.providers.find((provider) => provider.id === id);
          const label = live ? (live.connected ? "Connected" : "Offline") : state === "Planned" ? "Planned" : "Not configured";
          return <article className="provider-card" key={id}>
            <div className="provider-card-top"><span className="provider-icon"><Icon size={17} /></span><span className={live?.connected ? "provider-state connected" : "provider-state"}>{label}</span></div>
            <strong>{name}</strong><p>{detail}</p><code>{id}</code>
            {live && <small className="provider-model-count">{live.models.length} models available</small>}
          </article>;
        })}
      </div>
      <div className="provider-active-row"><label className="provider-field"><span>Shared active provider · Chat + Agent</span>
        <select value={activeProvider} onChange={(event) => onProviderChange(event.target.value)}>
          {(catalog?.providers ?? []).map((provider) => <option key={provider.id} value={provider.id}>{provider.name}{provider.connected ? " · Connected" : " · Offline"}</option>)}
        </select>
      </label><small>Both Chat and Agent use this same provider selection.</small></div>
      <div className="provider-note"><AlertCircle size={15} /><span>Registry and adapter contracts are in place. Provider credentials, live connection tests and Chat/Agent routing will be connected in the next integration step.</span></div>
    </section>

    <section className="panel switching-panel">
      <div className="panel-header"><div><h2>Switching policy</h2><p>Control exactly when NEXUS may move to another provider</p></div><ShieldCheck size={18} className="panel-muted-icon" /></div>
      <div className="provider-settings">
        <label className="provider-field"><span>Automatic switching mode</span>
          <select value={policy.mode} onChange={(e) => update("mode", e.target.value as SwitchingMode)}>
            <option value="disabled">Disabled</option><option value="manual_only">Manual only</option>
            <option value="error_triggered">Error-triggered</option><option value="exception_based">Exception allowlist</option>
            <option value="guided">Guided · ask before switching</option>
          </select>
        </label>
        <div className="provider-number-grid">
          <label className="provider-field"><span>Max switches / request</span><input type="number" min={0} max={5} value={policy.max_switches_per_request} onChange={(e) => update("max_switches_per_request", Number(e.target.value))} /></label>
          <label className="provider-field"><span>Retries before fallback</span><input type="number" min={0} max={10} value={policy.retry_limit} onChange={(e) => update("retry_limit", Number(e.target.value))} /></label>
          <label className="provider-field"><span>Cooldown (seconds)</span><input type="number" min={0} max={3600} value={policy.cooldown_seconds} onChange={(e) => update("cooldown_seconds", Number(e.target.value))} /></label>
        </div>
        <label className="provider-field"><span>Allowed switching path</span><input value={pathText} onChange={(e) => { setPathText(e.target.value); setSaved(false); }} placeholder="openai-compatible → ollama-kaggle → anthropic" />
          <small>Only the listed order is eligible. Leave empty to block all automatic transitions.</small>
        </label>
        {policy.mode === "exception_based" && <fieldset className="provider-exceptions"><legend>Allowed failure types</legend>
          {FAILURE_OPTIONS.map(({ value, label }) => <label key={value}><input type="checkbox" checked={policy.exception_allowlist.includes(value)} onChange={(e) => toggleFailure(value, e.target.checked)} />{label}</label>)}
        </fieldset>}
        <label className="provider-toggle"><input type="checkbox" checked={policy.require_confirmation} onChange={(e) => update("require_confirmation", e.target.checked)} /><span><strong>Require confirmation</strong><small>Ask before every automatic fallback, regardless of mode.</small></span></label>
        <div className="provider-safety"><ShieldCheck size={16} /><span>Isolation, pending approvals, authentication failures, security blocks and user cancellation always stop fallback. Switching after a response stream begins is prohibited.</span></div>
        {error && <div className="error-banner provider-error">{error}</div>}
        <div className="provider-save-row">{saved && <span className="provider-saved"><Check size={14} />Saved</span>}<button className="primary-button" onClick={() => void save()} disabled={loading || saving}><Save size={14} />{saving ? "Saving…" : "Save policy"}</button></div>
      </div>
    </section>
    <div className="provider-footnote"><ChevronRight size={14} /> Provider policy is enforced server-side; UI settings are not a security boundary.</div>
  </div>;
}
