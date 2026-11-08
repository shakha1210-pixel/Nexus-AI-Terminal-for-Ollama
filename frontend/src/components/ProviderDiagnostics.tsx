import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, RefreshCw, Timer } from "lucide-react";
import { api } from "../services/api";
import { useTranslation } from "../i18n";

type Diagnostic = {
  provider_id: string;
  connected: boolean | null;
  state: "available" | "cooldown";
  cooldown_remaining_seconds: number;
  consecutive_failures: number;
  last_error_kind: string | null;
  last_error: string | null;
  last_success: boolean;
  recommendations: { code: string; level: "warning" | "error"; message: string }[];
};

export default function ProviderDiagnostics() {
  const { t } = useTranslation();
  const [items, setItems] = useState<Diagnostic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const result = await api.getProviderDiagnostics();
      setItems(result.providers);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("diagnostics.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      setItems((current) => current.map((item) => ({
        ...item,
        cooldown_remaining_seconds: Math.max(0, item.cooldown_remaining_seconds - 1),
        state: item.cooldown_remaining_seconds <= 1 ? "available" : item.state,
      })));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return <section className="panel diagnostics-panel">
    <div className="panel-header"><div><h2>{t("diagnostics.title")}</h2><p>{t("diagnostics.subtitle")}</p></div><Activity size={18} className="panel-muted-icon" /></div>
    <div className="diagnostics-list">
      {items.map((item) => <article className="diagnostic-row" key={item.provider_id}>
        <div className="diagnostic-top">
          <strong>{item.provider_id}</strong>
          <span className={item.state === "cooldown" ? "diagnostic-state cooling" : "diagnostic-state"}>
            {item.state === "cooldown" ? <><Timer size={13} /> {t("diagnostics.cooldown")}</> : <><CheckCircle2 size={13} /> {t("diagnostics.available")}</>}
          </span>
        </div>
        <div className="diagnostic-meta">
          <span>{t("diagnostics.connection")}: {item.connected === null ? "—" : item.connected ? t("status.connected") : t("status.offline")}</span>
          <span>{t("diagnostics.failures")}: {item.consecutive_failures}</span>
          {item.state === "cooldown" && <strong>{t("diagnostics.remaining").replace("{seconds}", item.cooldown_remaining_seconds.toFixed(0))}</strong>}
          {item.last_error_kind && <span>{t("diagnostics.lastError")}: {item.last_error_kind}</span>}
        </div>
        {item.recommendations.map((tip) => <div className={tip.level === "error" ? "diagnostic-tip is-error" : "diagnostic-tip"} key={tip.code}><AlertTriangle size={14} /><span>{t(`diagnostics.tip.${tip.code}`)}</span></div>)}
      </article>)}
      {!loading && items.length === 0 && <p className="diagnostics-empty">{t("diagnostics.empty")}</p>}
    </div>
    {error && <div className="error-banner diagnostics-error">{error}</div>}
    <div className="diagnostics-footer"><span>{t("diagnostics.noBlockingWait")}</span><button className="workspace-icon-btn" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} /> {t("actions.refresh")}</button></div>
  </section>;
}
