import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, ChevronRight, Cpu, Network, Save, ShieldCheck, Workflow } from "lucide-react";
import { api } from "../services/api";
import type { FailureKind, ProviderCatalog, ProviderPolicy, SwitchingMode } from "../types/providers";
import { useTranslation } from "../i18n";
import ProviderDiagnostics from "./ProviderDiagnostics";

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
  const { t } = useTranslation();
  const failureLabel = (value: FailureKind) => ({ timeout: t("providers.failureTimeout"), rate_limit: t("providers.failureRateLimit"), server_error: t("providers.failureServer"), network_error: t("providers.failureNetwork"), authentication: t("providers.failureAuthentication"), model_not_found: t("providers.failureModelMissing"), user_cancelled: t("providers.failureCancelled"), security_block: t("providers.failureSecurity"), unknown: t("providers.failureUnknown") })[value];
  const providerName = (id: string, fallback: string) => (({ ollama: t("providers.ollamaName"), "openai-compatible": t("providers.openaiName"), anthropic: t("providers.anthropicName"), gemini: t("providers.geminiName") } as Record<string, string>)[id] ?? fallback);
  const providerDetail = (id: string, fallback: string) => (({ ollama: t("providers.ollamaDetail"), "openai-compatible": t("providers.openaiDetail"), anthropic: t("providers.anthropicDetail"), gemini: t("providers.geminiDetail") } as Record<string, string>)[id] ?? fallback);
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
      if (active) setError(e instanceof Error ? e.message : t("providers.policyLoadError"));
    }).finally(() => { if (active) setLoading(false); });
    void api.getProviderCatalog().then((value) => { if (active) setCatalog(value); }).catch((e: unknown) => {
      if (active) setError(e instanceof Error ? e.message : t("providers.catalogLoadError"));
    });
    return () => { active = false; };
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
    } catch (e) { setError(e instanceof Error ? e.message : t("providers.policySaveError")); }
    finally { setSaving(false); }
  };

  const toggleFailure = (value: FailureKind, checked: boolean) => {
    update("exception_allowlist", checked
      ? [...policy.exception_allowlist, value]
      : policy.exception_allowlist.filter((item) => item !== value));
  };

  return <div className="provider-page">
    <section className="panel provider-panel">
      <div className="panel-header"><div><h2>{t("providers.registry")}</h2><p>{t("providers.registrySubtitle")}</p></div><Network size={18} className="panel-muted-icon" /></div>
      <div className="provider-grid">
        {PROVIDERS.map(({ id, name, detail, icon: Icon, state }) => {
          const live = catalog?.providers.find((provider) => provider.id === id);
          const label = live ? (live.connected ? t("status.connected") : t("status.offline")) : state === "Planned" ? t("providers.planned") : t("providers.notConfigured");
          return <article className="provider-card" key={id}>
            <div className="provider-card-top"><span className="provider-icon"><Icon size={17} /></span><span className={live?.connected ? "provider-state connected" : "provider-state"}>{label}</span></div>
            <strong>{providerName(id, name)}</strong><p>{providerDetail(id, detail)}</p><code>{id}</code>
            {live && <small className="provider-model-count">{t("providers.modelsAvailable").replace("{count}", String(live.models.length))}</small>}
          </article>;
        })}
      </div>
      <div className="provider-active-row"><label className="provider-field"><span>{t("providers.sharedProvider")}</span>
        <select value={activeProvider} onChange={(event) => onProviderChange(event.target.value)}>
          {(catalog?.providers ?? []).map((provider) => <option key={provider.id} value={provider.id}>{provider.name}{provider.connected ? ` · ${t("status.connected")}` : ` · ${t("status.offline")}`}</option>)}
        </select>
      </label><small>{t("providers.sharedProviderNote")}</small></div>
      <div className="provider-note"><AlertCircle size={15} /><span>{t("providers.adapterNote")}</span></div>
    </section>

    <section className="panel switching-panel">
      <div className="panel-header"><div><h2>{t("providers.switchingPolicy")}</h2><p>{t("providers.switchingSubtitle")}</p></div><ShieldCheck size={18} className="panel-muted-icon" /></div>
      <div className="provider-settings">
        <label className="provider-field"><span>{t("providers.switchMode")}</span>
          <select value={policy.mode} onChange={(e) => update("mode", e.target.value as SwitchingMode)}>
            <option value="disabled">{t("providers.disabled")}</option><option value="manual_only">{t("providers.manualOnly")}</option>
            <option value="error_triggered">{t("providers.errorTriggered")}</option><option value="exception_based">{t("providers.exceptionAllowlist")}</option>
            <option value="guided">{t("providers.guided")}</option>
          </select>
        </label>
        <div className="provider-number-grid">
          <label className="provider-field"><span>{t("providers.maxSwitches")}</span><input type="number" min={0} max={5} value={policy.max_switches_per_request} onChange={(e) => update("max_switches_per_request", Number(e.target.value))} /></label>
          <label className="provider-field"><span>{t("providers.retries")}</span><input type="number" min={0} max={10} value={policy.retry_limit} onChange={(e) => update("retry_limit", Number(e.target.value))} /></label>
          <label className="provider-field"><span>{t("providers.cooldown")}</span><input type="number" min={0} max={3600} value={policy.cooldown_seconds} onChange={(e) => update("cooldown_seconds", Number(e.target.value))} /><small>{t("providers.cooldownHelp")}</small></label>
        </div>
        <label className="provider-field"><span>{t("providers.allowedPath")}</span><input value={pathText} onChange={(e) => { setPathText(e.target.value); setSaved(false); }} placeholder="openai-compatible → ollama" />
          <small>{t("providers.pathHelp")}</small>
        </label>
        {policy.mode === "exception_based" && <fieldset className="provider-exceptions"><legend>{t("providers.failureTypes")}</legend>
          {FAILURE_OPTIONS.map(({ value }) => <label key={value}><input type="checkbox" checked={policy.exception_allowlist.includes(value)} onChange={(e) => toggleFailure(value, e.target.checked)} />{failureLabel(value)}</label>)}
        </fieldset>}
        <label className="provider-toggle"><input type="checkbox" checked={policy.require_confirmation} onChange={(e) => update("require_confirmation", e.target.checked)} /><span><strong>{t("providers.requireConfirmation")}</strong><small>{t("providers.confirmationHelp")}</small></span></label>
        <div className="provider-safety"><ShieldCheck size={16} /><span>{t("providers.safetyNote")}</span></div>
        {error && <div className="error-banner provider-error">{error}</div>}
        <div className="provider-save-row">{saved && <span className="provider-saved"><Check size={14} />{t("actions.saved")}</span>}<button className="primary-button" onClick={() => void save()} disabled={loading || saving}><Save size={14} />{saving ? t("actions.saving") : t("providers.savePolicy")}</button></div>
      </div>
    </section>
    <ProviderDiagnostics />
    <div className="provider-footnote"><ChevronRight size={14} /> {t("providers.serverEnforced")}</div>
  </div>;
}
