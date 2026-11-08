import { useState } from "react";
import { Cloud, Play, Repeat } from "lucide-react";
import { api } from "../services/api";
import type { KaggleStatus } from "../types/kaggle";

const MODELS = ["llama3.2", "llama3.1:8b", "qwen2.5:7b", "mistral", "gemma2:9b"];
const BUSY = ["pushing", "queued", "starting"];

const LABELS: Record<string, string> = {
  idle: "Not started", pushing: "Uploading", queued: "Queued",
  starting: "Starting", online: "Online", stopped: "Stopped", error: "Error",
};

type Props = {
  status: KaggleStatus | null;
  onStatusChange: (status: KaggleStatus) => void;
  onModeChange: () => void;
};

export default function KagglePanel({ status, onStatusChange, onModeChange }: Props) {
  const [model, setModel] = useState(MODELS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const act = async (fn: () => Promise<KaggleStatus>) => {
    setBusy(true);
    setError(null);
    try {
      onStatusChange(await fn());
      onModeChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  };

  const state = status?.state ?? "idle";
  const inProgress = BUSY.includes(state);

  return (
    <section className="panel kaggle-panel" id="kaggle">
      <div className="panel-header">
        <div><h2>Kaggle GPU</h2><p>Remote Ollama runtime (OpenAI-compatible /v1)</p></div>
        <Cloud size={18} className="panel-muted-icon" />
      </div>
      <div className="kaggle-body">
        <div className="kaggle-state">
          <span className={`status-dot ${state === "online" ? "online" : state === "error" ? "offline" : ""}`} />
          <strong>{LABELS[state]}</strong>
          <span className="kaggle-msg">{status?.message}</span>
        </div>
        <label className="kaggle-field">
          <span>Model</span>
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={inProgress || busy}>
            {MODELS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <div className="kaggle-actions">
          <button className="primary-button" disabled={inProgress || busy} onClick={() => void act(() => api.startKaggle(model))}>
            <Play size={15} />Launch on Kaggle
          </button>
          <button className="secondary-button" disabled={busy || (state !== "online" && status?.mode !== "kaggle")}
            onClick={() => void act(() => api.setMode(status?.mode === "kaggle" ? "local" : "kaggle"))}>
            <Repeat size={15} />{status?.mode === "kaggle" ? "Switch to local" : "Use Kaggle runtime"}
          </button>
        </div>
        {status?.openai_base_url && <div className="detail-row"><span>OpenAI base URL</span><code>{status.openai_base_url}</code></div>}
        {error && <div className="error-banner kaggle-error">{error}</div>}
      </div>
    </section>
  );
}
