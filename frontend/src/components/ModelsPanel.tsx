import { useState } from "react";
import { Boxes, Cpu, Download, RefreshCw, Trash2 } from "lucide-react";
import type { OllamaModel } from "../types/ollama";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
type Props = { models: OllamaModel[]; connected: boolean; onRefresh: () => void };

function formatBytes(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes)) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export default function ModelsPanel({ models, connected, onRefresh }: Props) {
  const [modelName, setModelName] = useState("");
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const pullModel = async () => {
    const name = modelName.trim();
    if (!name || pulling || !connected) return;
    setPulling(true); setError(""); setProgress("Connecting to Ollama…");
    try {
      const response = await fetch(`${API_BASE}/api/ollama/models/pull`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? `API error: ${response.status}`);
      }
      if (!response.body) throw new Error("Streaming response is not available.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let succeeded = false;
      const consume = (line: string) => {
        if (!line.startsWith("data:")) return;
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") return;
        const payload = JSON.parse(raw) as { status?: string; total?: number; completed?: number; error?: string };
        if (payload.error) throw new Error(payload.error);
        if (payload.total && payload.completed !== undefined) {
          setProgress(`${payload.status ?? "Downloading"} · ${Math.min(100, Math.round(payload.completed / payload.total * 100))}%`);
        } else if (payload.status) {
          setProgress(payload.status);
          if (payload.status === "success") succeeded = true;
        }
      };
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";
        for (const line of lines) consume(line);
        if (done) break;
      }
      if (buffer) consume(buffer);
      if (!succeeded) setProgress("Pull stream ended. Refreshing model list…");
      else setProgress("Model installed successfully.");
      setModelName("");
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Model yuklash amalga oshmadi.");
    } finally { setPulling(false); }
  };

  const deleteModel = async (name: string) => {
    if (!window.confirm(`“${name}” modelini Ollama’dan o‘chirasizmi?`)) return;
    setDeleting(name); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/ollama/models`, {
        method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail ?? `API error: ${response.status}`);
      }
      setProgress(`${name} removed.`);
      onRefresh();
    } catch (err) { setError(err instanceof Error ? err.message : "Modelni o‘chirish amalga oshmadi."); }
    finally { setDeleting(null); }
  };

  return <section className="panel models-panel" id="models">
    <div className="panel-header models-panel-header">
      <div><h2>Installed models</h2><p>Models available on the selected Ollama runtime</p></div>
      <button className="text-button" onClick={onRefresh}><RefreshCw size={13} /> Refresh</button>
    </div>
    <div className="model-pull-bar">
      <input aria-label="Ollama model name" value={modelName} onChange={(event) => setModelName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void pullModel(); }} placeholder="Model tag, e.g. llama3.2:latest" disabled={!connected || pulling} />
      <button className="model-pull-button" onClick={() => void pullModel()} disabled={!connected || pulling || !modelName.trim()}><Download size={14} /> {pulling ? "Pulling…" : "Pull model"}</button>
    </div>
    {progress && <div className="model-progress" role="status">{pulling && <span className="model-progress-dot" />}{progress}</div>}
    {error && <div className="model-error" role="alert">{error}</div>}
    {!connected ? (
      <div className="empty-state"><div className="empty-icon"><Cpu size={22} /></div><strong>Ollama is not connected</strong><p>Start Ollama and make sure its local API is available at <code>127.0.0.1:11434</code>.</p></div>
    ) : models.length === 0 ? (
      <div className="empty-state"><div className="empty-icon"><Boxes size={22} /></div><strong>No models found</strong><p>Enter a model tag above to download your first model.</p><code>llama3.2</code></div>
    ) : (
      <div className="model-list">{models.map((model) => (
        <div className="model-row" key={model.digest ?? model.name}>
          <div className="model-symbol"><Cpu size={17} /></div>
          <div className="model-info"><strong>{model.name}</strong><span>{[model.family, model.parameter_size, model.quantization_level].filter(Boolean).join(" · ") || "Local model"}</span></div>
          <span className="model-size">{formatBytes(model.size)}</span>
          <span className="model-ready"><span className="status-dot online" />Ready</span>
          <button className="model-delete-button" title={`Delete ${model.name}`} aria-label={`Delete ${model.name}`} disabled={deleting !== null} onClick={() => void deleteModel(model.name)}>{deleting === model.name ? <RefreshCw size={14} className="spin" /> : <Trash2 size={14} />}</button>
        </div>
      ))}</div>
    )}
    <div className="panel-footer"><span>{models.length} model{models.length === 1 ? "" : "s"} detected</span><span>Powered by Ollama</span></div>
  </section>;
}
