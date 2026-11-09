import { useState } from "react";
import { Cloud, Play, Repeat } from "lucide-react";
import { api } from "../services/api";
import type { KaggleState, KaggleStatus } from "../types/kaggle";
import { useTranslation } from "../i18n";
import KaggleNotebookLibrary from "./KaggleNotebookLibrary";

const MODELS = ["llama3.2", "llama3.1:8b", "qwen2.5:7b", "mistral", "gemma2:9b"];
const BUSY = ["pushing", "queued", "starting"];

export default function KagglePanel({ status, onStatusChange, onModeChange }: { status: KaggleStatus | null; onStatusChange: (status: KaggleStatus) => void; onModeChange: () => void }) {
  const { t } = useTranslation();
  const [model, setModel] = useState(MODELS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const act = async (fn: () => Promise<KaggleStatus>) => {
    setBusy(true); setError(null);
    try { onStatusChange(await fn()); onModeChange(); }
    catch (e) { setError(e instanceof Error ? e.message : t("kaggle.unknownError")); }
    finally { setBusy(false); }
  };

  const state: KaggleState = status?.state ?? "idle";
  const labels: Record<KaggleState, string> = { idle: t("kaggle.idle"), pushing: t("kaggle.pushing"), queued: t("kaggle.queued"), starting: t("kaggle.starting"), online: t("kaggle.online"), stopped: t("kaggle.stopped"), error: t("kaggle.error") };
  const inProgress = BUSY.includes(state);

  return (
    <>
    <section className="panel kaggle-panel" id="kaggle">
      <div className="panel-header">
        <div><h2>{t("kaggle.title")}</h2><p>{t("kaggle.subtitle")}</p></div>
        <Cloud size={18} className="panel-muted-icon" />
      </div>
      <div className="kaggle-body">
        <div className="kaggle-state">
          <span className={`status-dot ${state === "online" ? "online" : state === "error" ? "offline" : ""}`} />
          <strong>{labels[state]}</strong>
          <span className="kaggle-msg">{status?.message}</span>
        </div>
        <label className="kaggle-field">
          <span>{t("kaggle.model")}</span>
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={inProgress || busy}>
            {MODELS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <div className="kaggle-actions">
          <button className="primary-button" disabled={inProgress || busy} onClick={() => void act(() => api.startKaggle(model))}>
            <Play size={15} />{t("kaggle.start")}
          </button>
          <button className="secondary-button" disabled={busy || (state !== "online" && status?.mode !== "kaggle")}
            onClick={() => void act(() => api.setMode(status?.mode === "kaggle" ? "local" : "kaggle"))}>
            <Repeat size={15} />{status?.mode === "kaggle" ? t("kaggle.returnLocal") : t("kaggle.useRemote")}
          </button>
        </div>
        {status?.openai_base_url && <div className="detail-row"><span>{t("kaggle.baseUrl")}</span><code>{status.openai_base_url}</code></div>}
        {error && <div className="error-banner kaggle-error">{error}</div>}
      </div>
    </section>
    <KaggleNotebookLibrary />
    </>
  );
}
