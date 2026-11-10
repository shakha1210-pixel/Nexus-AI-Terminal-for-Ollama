import { useEffect, useRef, useState } from "react";
import { Bot, MessageSquare, Paperclip, Plus, RefreshCw, Send, Sparkles, Square, Trash2, X } from "lucide-react";
import type { OllamaModel } from "../types/ollama";
import { useTranslation } from "../i18n";
import { useAgentContext } from "../contexts/AgentContext";
import MarkdownMessage from "./MarkdownMessage";
import { openEventStream, readEventStream, request } from "../services/http";

type Message = { role: "user" | "assistant"; content: string };
type Conversation = { id: string; title: string; updated_at: string; message_count: number };

export default function ChatPanel({ models, connected, providerId }: { models: OllamaModel[]; connected: boolean; providerId: string }) {
  const { t } = useTranslation();
  const { agentId, setAgentId } = useAgentContext();
  const [model, setModel] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [availablePaths, setAvailablePaths] = useState<string[]>([]);
  const [attachmentsOpen, setAttachmentsOpen] = useState(false);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);
  const abortController = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!model && models.length) setModel(models[0].name);
    if (model && !models.some((item) => item.name === model)) setModel(models[0]?.name ?? "");
  }, [models, model]);

  const refreshHistory = async () => {
    try { setConversations(await request<Conversation[]>("/api/chat/conversations")); }
    catch (err) { setError(err instanceof Error ? err.message : t("chat.historyLoadError")); }
  };
  useEffect(() => { void refreshHistory(); }, []);
  useEffect(() => () => { abortController.current?.abort(); }, []);
  useEffect(() => {
    setSelectedPaths([]);
    setAvailablePaths([]);
    setAttachmentsOpen(false);
  }, [agentId]);

  const loadAvailableAttachments = async () => {
    setAttachmentsLoading(true);
    try {
      const result = await request<{ permissions: { path: string; access: string }[] }>(
        `/api/agents/${encodeURIComponent(agentId)}/permissions`
      );
      const paths = result.permissions
        .filter((permission) => permission.access === "read")
        .map((permission) => permission.path)
        .sort((a, b) => a.localeCompare(b));
      setAvailablePaths(paths);
      setAttachmentsOpen(true);
      if (!paths.length) setError(t("chat.noReadableFiles"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("chat.attachmentsLoadError"));
    } finally {
      setAttachmentsLoading(false);
    }
  };

  const toggleAttachmentPicker = () => {
    if (attachmentsOpen) {
      setAttachmentsOpen(false);
      return;
    }
    if (availablePaths.length) {
      setAttachmentsOpen(true);
      return;
    }
    void loadAvailableAttachments();
  };

  const toggleAttachment = (path: string) => {
    setSelectedPaths((current) => {
      if (current.includes(path)) return current.filter((item) => item !== path);
      if (current.length >= 10) return current;
      return [...current, path];
    });
  };
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: busy ? "auto" : "smooth", block: "end" });
  }, [messages, busy]);

  const openConversation = async (id: string) => {
    abortController.current?.abort();
    try {
      const result = await request<{ id: string; messages: Message[] }>(`/api/chat/conversations/${id}`);
      setConversationId(result.id);
      setMessages(result.messages.filter((item) => item.role === "user" || item.role === "assistant"));
      setError("");
      setRetryPrompt(null);
    } catch (err) { setError(err instanceof Error ? err.message : t("chat.openError")); }
  };

  const newConversation = () => {
    abortController.current?.abort();
    setConversationId(null);
    setMessages([]);
    setDraft("");
    setError("");
    setRetryPrompt(null);
  };

  const deleteConversation = async (id: string) => {
    if (!window.confirm(t("chat.deleteConfirm"))) return;
    try {
      await request<{ deleted: string }>(`/api/chat/conversations/${id}`, { method: "DELETE" });
      if (conversationId === id) newConversation();
      await refreshHistory();
    } catch (err) { setError(err instanceof Error ? err.message : t("chat.deleteError")); }
  };

  const stopGeneration = () => abortController.current?.abort();

  const sendMessage = async (messageOverride?: string, appendUser = true, retryLast = false) => {
    const text = (messageOverride ?? draft).trim();
    if (!text || !model || busy || abortController.current || !connected) return;
    const controller = new AbortController();
    abortController.current = controller;
    if (appendUser) {
      setDraft("");
      setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);
    } else {
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 && item.role === "assistant" ? { ...item, content: "" } : item
      ));
    }
    setError("");
    setRetryPrompt(null);
    setBusy(true);
    try {
      const response = await openEventStream("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_id: providerId, model, message: text, conversation_id: conversationId, agent_id: agentId, paths: selectedPaths, retry_last: retryLast }),
        signal: controller.signal,
      });
      let streamError = "";
      await readEventStream(response, ({ event, data }) => {
        if (!data) return;
        const payload = JSON.parse(data);
        if (event === "meta") setConversationId(payload.conversation_id);
        if (event === "token") setMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: item.content + payload.content } : item));
        if (event === "error") streamError = payload.message ?? t("chat.modelError");
      }, controller.signal);
      if (streamError) {
        setError(streamError);
        setRetryPrompt(text);
      }
      await refreshHistory();
    } catch (err) {
      if (controller.signal.aborted) {
        setError("");
        await refreshHistory();
      } else {
        setError(err instanceof Error ? err.message : t("chat.sendError"));
        setRetryPrompt(text);
        setMessages((current) => current.map((item, index) => index === current.length - 1 && item.role === "assistant" && !item.content ? { ...item, content: t("chat.responseError") } : item));
      }
    } finally {
      if (abortController.current === controller) abortController.current = null;
      setBusy(false);
    }
  };

  const retryLastMessage = () => {
    if (retryPrompt) void sendMessage(retryPrompt, false, Boolean(conversationId));
  };

  return <section className="chat-workspace">
    <aside className="chat-history">
      <div className="chat-history-head"><strong>{t("chat.conversations")}</strong><button onClick={newConversation} title={t("chat.newConversation")} disabled={busy}><Plus size={16} /></button></div>
      {conversations.map((item) => <div className={`chat-history-item ${conversationId === item.id ? "active" : ""}`} key={item.id}>
        <button className="chat-history-open" onClick={() => void openConversation(item.id)} disabled={busy}><MessageSquare size={14} /><span>{item.title || t("chat.newConversation")}</span></button>
        <button className="chat-history-delete" title={t("chat.deleteConversation")} onClick={() => void deleteConversation(item.id)} disabled={busy}><Trash2 size={13} /></button>
      </div>)}
      {!conversations.length && <p className="chat-history-empty">{t("chat.noSavedConversations")}</p>}
    </aside>
    <div className="chat-main">
      <div className="chat-toolbar">
        <div><p className="eyebrow">{t("chat.sharedProvider")} · {providerId}</p><h2>{t("nav.aiChat")}</h2></div>
        <label>{t("models.model")}<select value={model} onChange={(event) => setModel(event.target.value)} disabled={!models.length}>{models.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label>
      </div>
      <div className="chat-messages">
        {!messages.length && <div className="chat-empty">
          <div className="chat-empty-mark"><Sparkles size={25} /></div>
          <strong>{t("chat.welcomeTitle")}</strong>
          <p>{t("chat.welcomeSubtitle")}</p>
          <div className="chat-empty-suggestions">
            <button type="button" onClick={() => setDraft(t("chat.suggestionExplain"))}><MessageSquare size={14} />{t("chat.suggestionExplain")}</button>
            <button type="button" onClick={() => setDraft(t("chat.suggestionBuild"))}><Bot size={14} />{t("chat.suggestionBuild")}</button>
            <button type="button" onClick={() => setDraft(t("chat.suggestionAnalyze"))}><Paperclip size={14} />{t("chat.suggestionAnalyze")}</button>
          </div>
        </div>}
        {messages.map((item, index) => <article className={`chat-message ${item.role}`} key={index}><span>{item.role === "user" ? t("chat.you") : "NEXUS"}</span><MarkdownMessage content={item.content || (busy && index === messages.length - 1 ? t("chat.thinking") : "")} /></article>)}
        <div ref={messagesEndRef} aria-hidden="true" />
      </div>
      <div className="chat-composer">
        <details className="chat-advanced-context">
          <summary><Paperclip size={14} />{t("chat.advancedContext")}<span>{selectedPaths.length ? `${selectedPaths.length} ${t("chat.selectedAttachments")}` : t("chat.advancedContextNote")}</span></summary>
          <div className="chat-context-row">
            <label>{t("agent.id")} <input value={agentId} onChange={(event) => setAgentId(event.target.value)} maxLength={64} /></label>
            <div className="chat-attachment-control">
              <button type="button" className="chat-attach-toggle" onClick={toggleAttachmentPicker} disabled={attachmentsLoading || busy} aria-expanded={attachmentsOpen}>
                <Paperclip size={14} />{attachmentsLoading ? t("chat.attachmentsLoading") : t("chat.attachFiles")}
                <span>{selectedPaths.length}/10</span>
              </button>
              {attachmentsOpen && <div className="chat-attachment-picker">
                {!availablePaths.length ? <p>{t("chat.noReadableFiles")}</p> : availablePaths.map((path) => (
                  <label key={path} className="chat-attachment-option">
                    <input type="checkbox" checked={selectedPaths.includes(path)} disabled={!selectedPaths.includes(path) && selectedPaths.length >= 10} onChange={() => toggleAttachment(path)} />
                    <span>{path}</span>
                  </label>
                ))}
                <p className="chat-attachment-note">{t("chat.attachmentsPermissionNote")}</p>
              </div>}
            </div>
          </div>
        </details>
        {selectedPaths.length > 0 && <div className="chat-attachment-chips" aria-label={t("chat.selectedAttachments")}>
          {selectedPaths.map((path) => <span className="chat-attachment-chip" key={path}>
            <span>{path}</span><button type="button" title={t("chat.removeAttachment")} onClick={() => toggleAttachment(path)} disabled={busy}><X size={12} /></button>
          </span>)}
        </div>}
        <div className="chat-input-row"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.nativeEvent.keyCode !== 229) { event.preventDefault(); void sendMessage(); } }} placeholder={t("chat.promptPlaceholder")} rows={3} disabled={!connected || busy} />{busy ? <button className="primary-button chat-stop-button" onClick={stopGeneration}><Square size={16} />{t("chat.stop")}</button> : <button className="primary-button" onClick={() => void sendMessage()} disabled={!connected || !draft.trim() || !model}><Send size={16} />{t("chat.send")}</button>}</div>
        <p className="chat-footnote">{t("chat.footnote")}</p>
      </div>
      {error && <div className="chat-error" role="alert"><span>{error}</span>{retryPrompt && <button className="chat-retry-button" onClick={retryLastMessage} disabled={busy}><RefreshCw size={13} />{t("chat.retry")}</button>}</div>}
    </div>
  </section>;
}
