import { useEffect, useState } from "react";
import { Bot, MessageSquare, Plus, Send, Trash2 } from "lucide-react";
import type { OllamaModel } from "../types/ollama";
import { useTranslation } from "../i18n";
import { useAgentContext } from "../contexts/AgentContext";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
type Message = { role: "user" | "assistant"; content: string };
type Conversation = { id: string; title: string; updated_at: string; message_count: number };

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API xatosi: ${response.status}`);
  return response.json() as Promise<T>;
}

export default function ChatPanel({ models, connected, providerId }: { models: OllamaModel[]; connected: boolean; providerId: string }) {
  const { t } = useTranslation();
  const { agentId, setAgentId } = useAgentContext();
  const [model, setModel] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [agentId, setAgentId] = useState("default");
  const [pathsInput, setPathsInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!model && models.length) setModel(models[0].name);
    if (model && !models.some((item) => item.name === model)) setModel(models[0]?.name ?? "");
  }, [models, model]);

  const refreshHistory = async () => {
    try { setConversations(await apiGet<Conversation[]>("/api/chat/conversations")); }
    catch (err) { setError(err instanceof Error ? err.message : t("chat.historyLoadError")); }
  };
  useEffect(() => { void refreshHistory(); }, []);

  const openConversation = async (id: string) => {
    try {
      const result = await apiGet<{ id: string; messages: Message[] }>(`/api/chat/conversations/${id}`);
      setConversationId(result.id);
      setMessages(result.messages.filter((item) => item.role === "user" || item.role === "assistant"));
      setError("");
    } catch (err) { setError(err instanceof Error ? err.message : t("chat.openError")); }
  };

  const newConversation = () => {
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setError("");
  };

  const deleteConversation = async (id: string) => {
    if (!window.confirm(t("chat.deleteConfirm"))) return;
    try {
      const response = await fetch(`${API_BASE}/api/chat/conversations/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(t("chat.deleteError"));
      if (conversationId === id) newConversation();
      await refreshHistory();
    } catch (err) { setError(err instanceof Error ? err.message : t("chat.deleteError")); }
  };

  const sendMessage = async () => {
    const text = draft.trim();
    if (!text || !model || busy || !connected) return;
    setDraft("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setBusy(true);
    try {
      const paths = pathsInput.split(",").map((path) => path.trim()).filter(Boolean);
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_id: providerId, model, message: text, conversation_id: conversationId, agent_id: agentId, paths }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Chat API xatosi: ${response.status}`);
      }
      if (!response.body) throw new Error("Streaming javob mavjud emas.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamError = "";
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
          if (eventName === "meta") setConversationId(payload.conversation_id);
          if (eventName === "token") setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: item.content + payload.content } : item));
          if (eventName === "error") streamError = payload.message ?? t("chat.modelError");
        }
      }
      if (streamError) setError(streamError);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("chat.sendError"));
      setMessages((current) => current.map((item, index) => index === current.length - 1 && item.role === "assistant" && !item.content ? { ...item, content: t("chat.responseError") } : item));
    } finally { setBusy(false); }
  };

  return <section className="chat-workspace">
    <aside className="chat-history">
      <div className="chat-history-head"><strong>{t("chat.conversations")}</strong><button onClick={newConversation} title={t("chat.newConversation")}><Plus size={16} /></button></div>
      {conversations.map((item) => <div className={`chat-history-item ${conversationId === item.id ? "active" : ""}`} key={item.id}>
        <button className="chat-history-open" onClick={() => void openConversation(item.id)}><MessageSquare size={14} /><span>{item.title || t("chat.newConversation")}</span></button>
        <button className="chat-history-delete" title={t("chat.deleteConversation")} onClick={() => void deleteConversation(item.id)}><Trash2 size={13} /></button>
      </div>)}
      {!conversations.length && <p className="chat-history-empty">{t("chat.noSavedConversations")}</p>}
    </aside>
    <div className="chat-main">
      <div className="chat-toolbar">
        <div><p className="eyebrow">{t("chat.sharedProvider")} · {providerId}</p><h2>{t("nav.aiChat")}</h2></div>
        <label>{t("models.model")}<select value={model} onChange={(event) => setModel(event.target.value)} disabled={!models.length}>{models.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label>
      </div>
      <div className="chat-messages">
        {!messages.length && <div className="chat-empty"><Bot size={34} /><strong>{t("chat.startConversation")}</strong><p>{t("chat.routingInfo")}</p></div>}
        {messages.map((item, index) => <article className={`chat-message ${item.role}`} key={index}><span>{item.role === "user" ? t("chat.you") : "NEXUS"}</span><p>{item.content || (busy && index === messages.length - 1 ? t("chat.thinking") : "")}</p></article>)}
      </div>
      <div className="chat-composer">
        <div className="chat-context-row">
          <label>{t("agent.id")} <input value={agentId} onChange={(event) => setAgentId(event.target.value)} maxLength={64} /></label>
          <label className="chat-path-field">{t("chat.workspacePaths")} <input value={pathsInput} onChange={(event) => setPathsInput(event.target.value)} placeholder={t("chat.pathsPlaceholder")} /></label>
        </div>
        <div className="chat-input-row"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }} placeholder={t("chat.promptPlaceholder")} rows={3} disabled={!connected || busy} /><button className="primary-button" onClick={() => void sendMessage()} disabled={!connected || busy || !draft.trim() || !model}><Send size={16} />{busy ? t("chat.generating") : t("chat.send")}</button></div>
        <p className="chat-footnote">{t("chat.footnote")}</p>
      </div>
      {error && <div className="chat-error" role="alert">{error}</div>}
    </div>
  </section>;
}
