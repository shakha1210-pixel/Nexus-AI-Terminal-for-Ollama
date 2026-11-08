import { useEffect, useState } from "react";
import { Bot, Play, ShieldCheck, Wrench } from "lucide-react";
import type { OllamaModel } from "../types/ollama";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type ApprovalRequest = {
  request_id: string;
  path: string;
  operation: string;
  proposed_content: string;
  status: string;
  created_at: string;
  expires_at: string;
};

export default function AgentPanel({ models, connected }: { models: OllamaModel[]; connected: boolean }) {
  const [agentId, setAgentId] = useState("default");
  const [model, setModel] = useState("");
  const [task, setTask] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<"read_only" | "approval_required" | "autopilot" | "locked">("read_only");
  const [isolated, setIsolated] = useState(false);
  const [controlBusy, setControlBusy] = useState(false);
  const [controlMessage, setControlMessage] = useState("");
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [approvalBusy, setApprovalBusy] = useState<string | null>(null);
  const [approvalMessage, setApprovalMessage] = useState("");

  const loadApprovals = async () => {
    try {
      const response = await fetch(API_BASE + "/api/agents/" + encodeURIComponent(agentId) + "/approvals");
      if (!response.ok) return;
      const data = await response.json();
      setApprovals(Array.isArray(data.requests) ? data.requests : []);
    } catch { /* queue remains unavailable until backend responds */ }
  };

  const decideApproval = async (requestId: string, approve: boolean) => {
    setApprovalBusy(requestId);
    setApprovalMessage("");
    try {
      const response = await fetch(API_BASE + "/api/agents/" + encodeURIComponent(agentId) + "/approvals/" + requestId + "/decision", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approve }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Approval decision failed.");
      setApprovalMessage(approve ? "Approved: the exact proposed content was written." : "Proposal rejected; the file was not changed.");
      await loadApprovals();
    } catch (err) {
      setApprovalMessage(err instanceof Error ? err.message : "Approval error.");
      await loadApprovals();
    } finally { setApprovalBusy(null); }
  };

  const loadControl = async () => {
    try {
      const response = await fetch(API_BASE + "/api/agents/" + encodeURIComponent(agentId) + "/control");
      if (!response.ok) return;
      const data = await response.json();
      setMode(data.mode);
      setIsolated(Boolean(data.isolated));
    } catch { /* conservative default */ }
  };

  useEffect(() => { void loadControl(); }, [agentId]);
  useEffect(() => { void loadApprovals(); }, [agentId, mode]);

  const updateMode = async (nextMode: typeof mode) => {
    setControlBusy(true);
    setControlMessage("");
    try {
      const response = await fetch(API_BASE + "/api/agents/" + encodeURIComponent(agentId) + "/control/mode", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: nextMode }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Access mode o‘zgarmadi.");
      setMode(data.mode); setIsolated(Boolean(data.isolated)); setControlMessage("Access mode updated.");
    } catch (err) { setControlMessage(err instanceof Error ? err.message : "Control error."); }
    finally { setControlBusy(false); }
  };

  const setIsolation = async (nextIsolated: boolean) => {
    setControlBusy(true); setControlMessage("");
    try {
      const endpoint = nextIsolated ? "isolate" : "release";
      const response = await fetch(API_BASE + "/api/agents/" + encodeURIComponent(agentId) + "/" + endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextIsolated ? { reason: "Manual isolation from NEXUS UI" } : {}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Isolation state update failed.");
      setMode(data.mode); setIsolated(Boolean(data.isolated));
      setControlMessage(nextIsolated ? "Agent isolated; active Ollama request cancelled." : "Agent released in read-only mode.");
    } catch (err) { setControlMessage(err instanceof Error ? err.message : "Isolation error."); }
    finally { setControlBusy(false); }
  };

  useEffect(() => {
    if (!model && models.length) setModel(models[0].name);
    if (model && !models.some((item) => item.name === model)) setModel(models[0]?.name ?? "");
  }, [models, model]);

  const runAgent = async () => {
    if (!task.trim() || !model || !connected || running || isolated || mode === "locked") return;
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
          if (eventName === "approval") {
            setStatus(payload.message ?? "Edit proposal submitted for approval.");
            void loadApprovals();
          }
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
      <label>Access mode<select value={mode} onChange={(event) => void updateMode(event.target.value as typeof mode)} disabled={controlBusy || isolated}>
        <option value="read_only">Read-only</option><option value="approval_required">Approval required</option><option value="autopilot">Autopilot</option><option value="locked">Locked</option>
      </select></label>
      <div className="agent-control-actions"><button className={isolated ? "secondary-button" : "danger-button"} onClick={() => void setIsolation(!isolated)} disabled={controlBusy}>{isolated ? "Release agent" : "Isolate agent"}</button><span className={isolated ? "agent-isolation-state active" : "agent-isolation-state"}>{isolated ? "ISOLATED" : mode.toUpperCase()}</span></div>
    </div>
    {controlMessage && <p className="agent-control-message" role="status">{controlMessage}</p>}
    {mode === "approval_required" && <section className="agent-approval-queue" aria-label="File edit approval queue">
      <div className="agent-approval-heading"><div><strong>Approval Queue</strong><small>Har bir tasdiq faqat ko‘rsatilgan fayl va mazmun uchun bir marta amal qiladi.</small></div><button type="button" onClick={() => void loadApprovals()}>Refresh</button></div>
      {approvalMessage && <p className="agent-control-message" role="status">{approvalMessage}</p>}
      {!approvals.length && <p className="agent-approval-empty">Pending approval yo‘q.</p>}
      {approvals.map((item) => <article className="agent-approval-item" key={item.request_id}>
        <div className="agent-approval-meta"><strong>{item.path}</strong><span>Expires: {new Date(item.expires_at).toLocaleTimeString()}</span></div>
        <pre>{item.proposed_content}</pre>
        <div className="agent-approval-actions">
          <button type="button" className="secondary-button" disabled={approvalBusy !== null} onClick={() => void decideApproval(item.request_id, false)}>Reject</button>
          <button type="button" className="primary-button" disabled={approvalBusy !== null} onClick={() => void decideApproval(item.request_id, true)}>{approvalBusy === item.request_id ? "Applying…" : "Approve exact edit"}</button>
        </div>
      </article>)}
    </section>}
    <label className="agent-task-label">Task<textarea value={task} onChange={(event) => setTask(event.target.value)} rows={5} maxLength={12000} placeholder="Example: Read the files I have granted access to and summarize the project structure." disabled={running || !connected || isolated || mode === "locked"} /></label>
    <div className="agent-runtime-actions"><span className="agent-runtime-status">{running ? <><span className="agent-pulse" />{status}</> : status || "Ready"}</span><button className="primary-button" onClick={() => void runAgent()} disabled={!connected || running || isolated || mode === "locked" || !model || !task.trim()}><Play size={15} />{running ? "Running…" : "Run agent"}</button></div>
    <div className="agent-capabilities">
      <div><ShieldCheck size={17} /><span><strong>Access mode enforced</strong><small>Autopilot is still limited to explicitly granted read access in this build.</small></span></div>
      <div><Wrench size={17} /><span><strong>Isolation control</strong><small>Locks the agent and cancels its active Ollama request. No agent shell or external network tool exists.</small></span></div>
    </div>
    {output && <div className="agent-output"><div className="agent-output-title">AGENT RESPONSE</div><pre>{output}</pre></div>}
    {error && <div className="chat-error" role="alert">{error}</div>}
  </section>;
}
