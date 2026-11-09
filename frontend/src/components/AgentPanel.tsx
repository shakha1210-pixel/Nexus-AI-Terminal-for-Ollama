import { useEffect, useState } from "react";
import { Bot, Play, ShieldCheck, Wrench } from "lucide-react";
import type { OllamaModel } from "../types/ollama";
import { useTranslation } from "../i18n";
import { useAgentContext } from "../contexts/AgentContext";
import { openEventStream, readEventStream } from "../services/http";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

type ApprovalRequest = {
  request_id: string;
  path: string;
  operation: string;
  proposed_content: string;
  status: string;
  created_at: string;
  expires_at: string;
};

export default function AgentPanel({ models, connected, providerId }: { models: OllamaModel[]; connected: boolean; providerId: string }) {
  const { t } = useTranslation();
  const { agentId, setAgentId } = useAgentContext();
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
  const modeLabel = mode === "read_only" ? t("agent.readOnly") : mode === "approval_required" ? t("agent.approvalRequired") : mode === "autopilot" ? t("agent.autopilot") : t("agent.locked");

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
      if (!response.ok) throw new Error(data.detail ?? t("agent.approvalDecisionFailed"));
      setApprovalMessage(approve ? t("agent.approved") : t("agent.rejected"));
      await loadApprovals();
    } catch (err) {
      setApprovalMessage(err instanceof Error ? err.message : t("agent.approvalError"));
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
      if (!response.ok) throw new Error(data.detail ?? t("agent.modeError"));
      setMode(data.mode); setIsolated(Boolean(data.isolated)); setControlMessage(t("agent.modeUpdated"));
    } catch (err) { setControlMessage(err instanceof Error ? err.message : t("agent.controlError")); }
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
      if (!response.ok) throw new Error(data.detail ?? t("agent.isolationUpdateError"));
      setMode(data.mode); setIsolated(Boolean(data.isolated));
      setControlMessage(nextIsolated ? t("agent.isolated") : t("agent.released"));
    } catch (err) { setControlMessage(err instanceof Error ? err.message : t("agent.isolationError")); }
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
    setStatus(t("agent.starting"));
    try {
      const response = await openEventStream("/api/agents/" + encodeURIComponent(agentId) + "/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_id: providerId, model, task: task.trim() }),
      });
      await readEventStream(response, ({ event, data }) => {
        if (!data) return;
        const payload = JSON.parse(data);
        if (event === "status") setStatus(payload.message);
        if (event === "tool") setStatus(t("agent.tool") + ": " + payload.name + " — " + payload.result);
        if (event === "token") setOutput((current) => current + payload.content);
        if (event === "approval") {
          setStatus(payload.error ?? payload.message ?? t("agent.proposalSubmitted"));
          void loadApprovals();
        }
        if (event === "error") setError(payload.message ?? t("agent.runError"));
        if (event === "done") setStatus(t("agent.completed").replace("{count}", String(payload.tool_calls)));
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("agent.startError"));
    } finally {
      setRunning(false);
    }
  };

  return <section className="agent-runtime">
    <div className="agent-runtime-header">
      <div><p className="eyebrow">{t("pages.controlledExecution")}</p><h2>{t("nav.agentRuntime")}</h2><p>{t("agent.intro")}</p></div>
      <div className="agent-runtime-icon"><Bot size={25} /></div>
    </div>
    <div className="agent-runtime-controls">
      <label>{t("agent.id")}<input value={agentId} onChange={(event) => setAgentId(event.target.value)} maxLength={64} /></label>
      <label>{t("agent.providerModel")} · {providerId}<select value={model} onChange={(event) => setModel(event.target.value)} disabled={!models.length}>{models.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label>
      <label>{t("agent.accessMode")}<select value={mode} onChange={(event) => void updateMode(event.target.value as typeof mode)} disabled={controlBusy || isolated}>
        <option value="read_only">{t("agent.readOnly")}</option><option value="approval_required">{t("agent.approvalRequired")}</option><option value="autopilot">{t("agent.autopilot")}</option><option value="locked">{t("agent.locked")}</option>
      </select></label>
      <div className="agent-control-actions"><button className={isolated ? "secondary-button" : "danger-button"} onClick={() => void setIsolation(!isolated)} disabled={controlBusy}>{isolated ? t("agent.release") : t("agent.isolate")}</button><span className={isolated ? "agent-isolation-state active" : "agent-isolation-state"}>{isolated ? t("agent.isolatedBadge") : modeLabel}</span></div>
    </div>
    {controlMessage && <p className="agent-control-message" role="status">{controlMessage}</p>}
    {(mode === "approval_required" || approvals.length > 0) && <section className="agent-approval-queue" aria-label={t("agent.approvalQueue")}>
      <div className="agent-approval-heading"><div><strong>{t("agent.approvalQueue")}</strong><small>{t("agent.approvalDescription")}</small></div><button type="button" onClick={() => void loadApprovals()}>{t("actions.refresh")}</button></div>
      {mode !== "approval_required" && <p className="agent-approval-empty">{t("agent.modeChanged")}</p>}
      {approvalMessage && <p className="agent-control-message" role="status">{approvalMessage}</p>}
      {!approvals.length && <p className="agent-approval-empty">{t("agent.noPending")}</p>}
      {approvals.map((item) => <article className="agent-approval-item" key={item.request_id}>
        <div className="agent-approval-meta"><strong>{item.path}</strong><span>{t("agent.expires")}: {new Date(item.expires_at).toLocaleTimeString()}</span></div>
        <pre>{item.proposed_content}</pre>
        <div className="agent-approval-actions">
          <button type="button" className="secondary-button" disabled={approvalBusy !== null} onClick={() => void decideApproval(item.request_id, false)}>{t("agent.reject")}</button>
          <button type="button" className="primary-button" disabled={approvalBusy !== null || mode !== "approval_required" || isolated} onClick={() => void decideApproval(item.request_id, true)}>{approvalBusy === item.request_id ? t("agent.applying") : t("agent.approveExact")}</button>
        </div>
      </article>)}
    </section>}
    <label className="agent-task-label">{t("agent.task")}<textarea value={task} onChange={(event) => setTask(event.target.value)} rows={5} maxLength={12000} placeholder={t("agent.taskPlaceholder")} disabled={running || !connected || isolated || mode === "locked"} /></label>
    <div className="agent-runtime-actions"><span className="agent-runtime-status">{running ? <><span className="agent-pulse" />{status}</> : status || t("agent.ready")}</span><button className="primary-button" onClick={() => void runAgent()} disabled={!connected || running || isolated || mode === "locked" || !model || !task.trim()}><Play size={15} />{running ? t("agent.running") : t("agent.run")}</button></div>
    <div className="agent-capabilities">
      <div><ShieldCheck size={17} /><span><strong>{t("agent.accessEnforced")}</strong><small>{t("agent.autopilotNote")}</small></span></div>
      <div><Wrench size={17} /><span><strong>{t("agent.isolationControl")}</strong><small>{t("agent.isolationNote")}</small></span></div>
    </div>
    {output && <div className="agent-output"><div className="agent-output-title">{t("agent.response")}</div><pre>{output}</pre></div>}
    {error && <div className="chat-error" role="alert">{error}</div>}
  </section>;
}
