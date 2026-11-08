import { useEffect, useState } from "react";
import { Bot, Play, ShieldCheck, Wrench } from "lucide-react";
import type { OllamaModel } from "../types/ollama";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function AgentPanel({ models, connected }: { models: OllamaModel[]; connected: boolean }) {
  const [agentId, setAgentId] = useState("default");
  const [model, setModel] = useState("");
  const [task, setTask] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!model && models.length) setModel(models[0].name);
    if (model && !models.some((item) => item.name === model)) setModel(models[0]?.name ?? "");
  }, [models, model]);

  const runAgent = async () => {
    if (!task.trim() || !model || !connected || running) return;
    setRunning(true);
    setOutput("");
    setError("");
    setStatus("Starting agent…");
    try {
      const response = await fetch(`${API_BASE}/api/agents/${encodeURIComponent(agentId)}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, task: task.trim() }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Agent API xatosi: ${response.status}`);
      }
      if (!response.body) throw new Error("Agent stream mavjud emas.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const event of events) {
          const eventName = event.match(/^event: (.+)$/m)?.[1];
          const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
          if (!dataLine) continue;
          const payload = JSON.parse(dataLine.slice(6));
          if (eventName === "status") setStatus(payload.message);
          if (eventName === "tool") setStatus(`Tool: ${payload.name} — ${payload.result}`);
          if (eventName === "token") setOutput((current) => current + payload.content);
          if (eventName === "error") setError(payload.message ?? "Agent xatoligi.");
          if (eventName === "done") setStatus(`Completed · ${payload.tool_calls} tool calls`);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent ishga tushmadi.");
    } finally {
      setRunning(false);
    }
  };

  return <section className="agent-runtime">
    <div className="agent-runtime-header">
      <div><p className="eyebrow">CONTROLLED EXECUTION</p><h2>Agent Runtime</h2><p>Give an agent a task. It can read only files explicitly granted to its Agent ID.</p></div>
      <div className="agent-runtime-icon"><Bot size={25} /></div>
    </div>
    <div className="agent-runtime-controls">
      <label>Agent ID<input value={agentId} onChange={(event) => setAgentId(event.target.value)} maxLength={64} /></label>
      <label>Local model<select value={model} onChange={(event) => setModel(event.target.value)} disabled={!models.length}>{models.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label>
    </div>
    <label className="agent-task-label">Task<textarea value={task} onChange={(event) => setTask(event.target.value)} rows={5} maxLength={12000} placeholder="Example: Read the files I have granted access to and summarize the project structure." disabled={running || !connected} /></label>
    <div className="agent-runtime-actions"><span className="agent-runtime-status">{running ? <><span className="agent-pulse" />{status}</> : status || "Ready"}</span><button className="primary-button" onClick={() => void runAgent()} disabled={!connected || running || !model || !task.trim()}><Play size={15} />{running ? "Running…" : "Run agent"}</button></div>
    <div className="agent-capabilities">
      <div><ShieldCheck size={17} /><span><strong>Permission checked</strong><small>Every file read is checked against this agent’s grants.</small></span></div>
      <div><Wrench size={17} /><span><strong>One tool available</strong><small>workspace_read_file only. No terminal, network, write, or delete tools.</small></span></div>
    </div>
    {output && <div className="agent-output"><div className="agent-output-title">AGENT RESPONSE</div><pre>{output}</pre></div>}
    {error && <div className="chat-error" role="alert">{error}</div>}
  </section>;
}
