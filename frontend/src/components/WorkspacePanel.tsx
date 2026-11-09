import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { File, FileImage, FilePlus2, Folder, FolderPlus, HardDrive, RefreshCw, Save, Upload, X } from "lucide-react";
import { useTranslation } from "../i18n";
import { useAgentContext } from "../contexts/AgentContext";
import { request } from "../services/http";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
type Entry = { name: string; path: string; kind: "file" | "directory"; size: number | null; modified_at: number };
type TreeResponse = { root_name: string; path: string; entries: Entry[] };
type OpenFile = { path: string; content: string; dirty: boolean };

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `API error: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
const prettySize = (size: number | null) => size === null ? "Folder" : size < 1024 ? `${size} B` : `${(size / 1024).toFixed(1)} KB`;

export default function WorkspacePanel() {
  const { t } = useTranslation();
  const { agentId, setAgentId } = useAgentContext();
  const [tree, setTree] = useState<TreeResponse | null>(null);
  const [currentPath, setCurrentPath] = useState("");
  const [activeFile, setActiveFile] = useState<OpenFile | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState("");
  const [readGranted, setReadGranted] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);
  const loadTree = useCallback(async (path = currentPath) => {
    setBusy(true);
    try {
      const result = await apiRequest<TreeResponse>(`/api/workspace/tree?path=${encodeURIComponent(path)}`);
      setTree(result);
      setCurrentPath(path);
      setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.openError")); }
    finally { setBusy(false); }
  }, [currentPath]);

  useEffect(() => { void loadTree(""); }, []); // initial workspace load

  const openFile = async (entry: Entry) => {
    if (activeFile?.dirty && !window.confirm(t("workspace.discardBeforeOpen"))) return;
    if (/\.(png|jpe?g|gif|webp|svg)$/i.test(entry.name)) {
      setActiveFile({ path: entry.path, content: "", dirty: false });
      setMessage("");
      return;
    }
    if (entry.size !== null && entry.size > 2 * 1024 * 1024) { setMessage(t("workspace.fileTooLarge")); return; }
    try {
      const result = await apiRequest<{ path: string; content: string }>(`/api/workspace/file?path=${encodeURIComponent(entry.path)}`);
      setActiveFile({ ...result, dirty: false });
      setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.fileOpenError")); }
  };
  const saveFile = async () => {
    if (!activeFile) return;
    setBusy(true);
    try {
      await apiRequest("/api/workspace/file", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: activeFile.path, content: activeFile.content }) });
      setActiveFile({ ...activeFile, dirty: false });
      setMessage(t("workspace.fileSaved"));
      await loadTree(currentPath);
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.saveError")); }
    finally { setBusy(false); }
  };
  const createFolder = async () => {
    const name = window.prompt(t("workspace.newFolderPrompt"));
    if (!name?.trim()) return;
    const path = [currentPath, name.trim()].filter(Boolean).join("/");
    try { await apiRequest("/api/workspace/directory", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) }); await loadTree(currentPath); }
    catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.createFolderError")); }
  };
  const createFile = async () => {
    const name = window.prompt(t("workspace.newFilePrompt"));
    if (!name?.trim()) return;
    const path = [currentPath, name.trim()].filter(Boolean).join("/");
    try {
      await apiRequest("/api/workspace/file", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path, content: "" }) });
      await loadTree(currentPath);
      const entry = { name: name.trim(), path, kind: "file" as const, size: 0, modified_at: Date.now() / 1000 };
      await openFile(entry);
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.createFileError")); }
  };
  const uploadFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (file.size > 10 * 1024 * 1024) throw new Error(t("workspace.uploadTooLarge").replace("{name}", file.name));
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
        await apiRequest("/api/workspace/upload", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ directory: currentPath, filename: file.name, data_base64: btoa(binary) }) });
      }
      setMessage(t("workspace.uploaded"));
      await loadTree(currentPath);
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.uploadError")); }
    finally { setBusy(false); if (uploadRef.current) uploadRef.current.value = ""; }
  };
  useEffect(() => {
    let active = true;
    setReadGranted(false);
    if (!activeFile) return () => { active = false; };
    void apiRequest<{ permissions: { path: string; access: string }[] }>(`/api/agents/${encodeURIComponent(agentId)}/permissions`)
      .then((result) => {
        if (active) setReadGranted(result.permissions.some((permission) => permission.path === activeFile.path && permission.access === "read"));
      })
      .catch(() => { if (active) setReadGranted(false); });
    return () => { active = false; };
  }, [agentId, activeFile?.path]);

  const grantAgentRead = async () => {
    if (!activeFile) return;
    try {
      const result = await apiRequest<{ permissions: { path: string; access: string }[] }>(`/api/agents/${encodeURIComponent(agentId)}/permissions/read`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: activeFile.path }),
      });
      setReadGranted(result.permissions.some((permission) => permission.path === activeFile.path));
      setMessage(t("workspace.readGranted").replace("{agent}", agentId));
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.grantError")); }
  };
  const revokeAgentRead = async () => {
    if (!activeFile) return;
    try {
      await apiRequest(`/api/agents/${encodeURIComponent(agentId)}/permissions/read?path=${encodeURIComponent(activeFile.path)}`, { method: "DELETE" });
      setReadGranted(false);
      setMessage(t("workspace.readRevoked"));
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.revokeError")); }
  };
  const prepareAgentContext = async () => {
    if (!activeFile || !readGranted) return;
    try {
      const result = await apiRequest<{ attachments: { name: string; kind: string }[] }>(`/api/agents/${encodeURIComponent(agentId)}/context`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ paths: [activeFile.path] }),
      });
      setMessage(t("workspace.contextPrepared").replace("{count}", String(result.attachments.length)));
    } catch (error) { setMessage(error instanceof Error ? error.message : t("workspace.contextError")); }
  };
  const visibleEntries = useMemo(() => (tree?.entries ?? []).filter((entry) => entry.name.toLowerCase().includes(filter.toLowerCase())), [tree, filter]);
  const crumbs = currentPath ? currentPath.split("/") : [];

  return <section className="workspace-panel" id="explorer">
    <div className="workspace-toolbar">
      <div className="workspace-title"><HardDrive size={17} /><div><strong>{t("nav.explorer")}</strong><span>{tree?.root_name ?? t("workspace.localWorkspace")}</span></div></div>
      <div className="workspace-actions">
        <button className="workspace-icon-btn" title={t("workspace.newFile")} onClick={() => void createFile()}><FilePlus2 size={15} /></button>
        <button className="workspace-icon-btn" title={t("workspace.newFolder")} onClick={() => void createFolder()}><FolderPlus size={15} /></button>
        <button className="workspace-icon-btn" title={t("workspace.uploadFiles")} onClick={() => uploadRef.current?.click()}><Upload size={15} /></button>
        <button className="workspace-icon-btn" title={t("actions.refresh")} onClick={() => void loadTree()} disabled={busy}><RefreshCw size={15} className={busy ? "spin" : ""} /></button>
        <input ref={uploadRef} type="file" multiple hidden onChange={(event) => void uploadFiles(event.target.files)} />
      </div>
    </div>
    <div className="workspace-breadcrumb"><button onClick={() => void loadTree("")}>{tree?.root_name ?? t("nav.workspaceTitle")}</button>{crumbs.map((part, index) => <span key={index}> / <button onClick={() => void loadTree(crumbs.slice(0, index + 1).join("/"))}>{part}</button></span>)}</div>
    <div className="workspace-body">
      <aside className="workspace-file-list">
        <input className="workspace-search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder={t("workspace.searchFiles")} />
        {visibleEntries.map((entry) => <button className={`workspace-file-entry ${activeFile?.path === entry.path ? "selected" : ""}`} key={entry.path} onClick={() => entry.kind === "directory" ? void loadTree(entry.path) : void openFile(entry)}>
          {entry.kind === "directory" ? <Folder size={15} /> : entry.name.match(/\.(png|jpe?g|gif|webp|svg)$/i) ? <FileImage size={15} /> : <File size={15} />}
          <span>{entry.name}</span><small>{prettySize(entry.size)}</small>
        </button>)}
        {!visibleEntries.length && <p className="workspace-empty">{t("workspace.emptyFolder")}</p>}
      </aside>
      <div className="workspace-editor">
        {activeFile ? <><div className="editor-tab"><File size={14} /><span>{activeFile.path.split("/").pop()}</span>{activeFile.dirty && <i /> }<button title={t("workspace.closeFile")} onClick={() => { if (!activeFile.dirty || window.confirm(t("workspace.discardChanges"))) setActiveFile(null); }}><X size={14} /></button><button className="save-file-button" onClick={() => void saveFile()} disabled={!activeFile.dirty || busy}><Save size={14} /> {t("actions.save")}</button></div>
          <div className="agent-handoff-bar">
            <label>{t("agent.id")} <input value={agentId} maxLength={64} onChange={(event) => setAgentId(event.target.value)} /></label>
            <button onClick={() => void (readGranted ? revokeAgentRead() : grantAgentRead())}>{readGranted ? t("workspace.revokeRead") : t("workspace.grantRead")}</button>
            <button onClick={() => void prepareAgentContext()} disabled={!readGranted}>{t("workspace.prepareContext")}</button>
            <span>{readGranted ? t("workspace.readAccessGranted") : t("workspace.noAccess")}</span>
          </div>
          {activeFile.path.match(/\.(png|jpe?g|gif|webp|svg)$/i) ? <div className="workspace-preview"><img className="workspace-image-preview" src={`${API_BASE}/api/workspace/asset?path=${encodeURIComponent(activeFile.path)}`} alt={activeFile.path.split("/").pop()} /><p>{t("workspace.imagePreview")}</p></div> :
          <textarea className="workspace-code-editor" spellCheck={false} value={activeFile.content} onChange={(event) => setActiveFile({ ...activeFile, content: event.target.value, dirty: true })} />}
        </> : <div className="workspace-welcome"><HardDrive size={32} /><strong>{t("workspace.localWorkspace")}</strong><p>{t("workspace.welcome")}</p><span>{t("workspace.directoryNote")}</span></div>}
      </div>
    </div>
    {message && <div className="workspace-message" role="status">{message}</div>}
  </section>;
}
