import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { File, FileImage, FilePlus2, Folder, FolderPlus, HardDrive, Image, RefreshCw, Save, Upload, X } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
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
  const [tree, setTree] = useState<TreeResponse | null>(null);
  const [currentPath, setCurrentPath] = useState("");
  const [activeFile, setActiveFile] = useState<OpenFile | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState("");
  const uploadRef = useRef<HTMLInputElement>(null);
  const loadTree = useCallback(async (path = currentPath) => {
    setBusy(true);
    try {
      const result = await apiRequest<TreeResponse>(`/api/workspace/tree?path=${encodeURIComponent(path)}`);
      setTree(result);
      setCurrentPath(path);
      setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Workspace ochilmadi."); }
    finally { setBusy(false); }
  }, [currentPath]);

  useEffect(() => { void loadTree(""); }, []); // initial workspace load

  const openFile = async (entry: Entry) => {
    if (entry.size !== null && entry.size > 2 * 1024 * 1024) { setMessage("2 MB dan katta fayllar hozircha matn muharririda ochilmaydi."); return; }
    try {
      const result = await apiRequest<{ path: string; content: string }>(`/api/workspace/file?path=${encodeURIComponent(entry.path)}`);
      setActiveFile({ ...result, dirty: false });
      setMessage("");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Fayl ochilmadi."); }
  };
  const saveFile = async () => {
    if (!activeFile) return;
    setBusy(true);
    try {
      await apiRequest("/api/workspace/file", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: activeFile.path, content: activeFile.content }) });
      setActiveFile({ ...activeFile, dirty: false });
      setMessage("Fayl saqlandi.");
      await loadTree(currentPath);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Saqlash amalga oshmadi."); }
    finally { setBusy(false); }
  };
  const createFolder = async () => {
    const name = window.prompt("Yangi papka nomi:");
    if (!name?.trim()) return;
    const path = [currentPath, name.trim()].filter(Boolean).join("/");
    try { await apiRequest("/api/workspace/directory", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path }) }); await loadTree(currentPath); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Papka yaratilmadi."); }
  };
  const createFile = async () => {
    const name = window.prompt("Yangi fayl nomi (masalan, notes.md):");
    if (!name?.trim()) return;
    const path = [currentPath, name.trim()].filter(Boolean).join("/");
    try {
      await apiRequest("/api/workspace/file", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path, content: "" }) });
      await loadTree(currentPath);
      const entry = { name: name.trim(), path, kind: "file" as const, size: 0, modified_at: Date.now() / 1000 };
      await openFile(entry);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Fayl yaratilmadi."); }
  };
  const uploadFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (file.size > 10 * 1024 * 1024) throw new Error(`${file.name}: 10 MB limitdan katta.`);
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
        await apiRequest("/api/workspace/upload", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ directory: currentPath, filename: file.name, data_base64: btoa(binary) }) });
      }
      setMessage("Fayllar workspace’ga yuklandi.");
      await loadTree(currentPath);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Yuklash amalga oshmadi."); }
    finally { setBusy(false); if (uploadRef.current) uploadRef.current.value = ""; }
  };
  const visibleEntries = useMemo(() => (tree?.entries ?? []).filter((entry) => entry.name.toLowerCase().includes(filter.toLowerCase())), [tree, filter]);
  const crumbs = currentPath ? currentPath.split("/") : [];

  return <section className="workspace-panel" id="explorer">
    <div className="workspace-toolbar">
      <div className="workspace-title"><HardDrive size={17} /><div><strong>Explorer</strong><span>{tree?.root_name ?? "Local workspace"}</span></div></div>
      <div className="workspace-actions">
        <button className="workspace-icon-btn" title="New file" onClick={() => void createFile()}><FilePlus2 size={15} /></button>
        <button className="workspace-icon-btn" title="New folder" onClick={() => void createFolder()}><FolderPlus size={15} /></button>
        <button className="workspace-icon-btn" title="Upload files" onClick={() => uploadRef.current?.click()}><Upload size={15} /></button>
        <button className="workspace-icon-btn" title="Refresh" onClick={() => void loadTree()} disabled={busy}><RefreshCw size={15} className={busy ? "spin" : ""} /></button>
        <input ref={uploadRef} type="file" multiple hidden onChange={(event) => void uploadFiles(event.target.files)} />
      </div>
    </div>
    <div className="workspace-breadcrumb"><button onClick={() => void loadTree("")}>{tree?.root_name ?? "Workspace"}</button>{crumbs.map((part, index) => <span key={index}> / <button onClick={() => void loadTree(crumbs.slice(0, index + 1).join("/"))}>{part}</button></span>)}</div>
    <div className="workspace-body">
      <aside className="workspace-file-list">
        <input className="workspace-search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Search files…" />
        {visibleEntries.map((entry) => <button className={`workspace-file-entry ${activeFile?.path === entry.path ? "selected" : ""}`} key={entry.path} onClick={() => entry.kind === "directory" ? void loadTree(entry.path) : void openFile(entry)}>
          {entry.kind === "directory" ? <Folder size={15} /> : entry.name.match(/\.(png|jpe?g|gif|webp|svg)$/i) ? <FileImage size={15} /> : <File size={15} />}
          <span>{entry.name}</span><small>{prettySize(entry.size)}</small>
        </button>)}
        {!visibleEntries.length && <p className="workspace-empty">This folder is empty.</p>}
      </aside>
      <div className="workspace-editor">
        {activeFile ? <><div className="editor-tab"><File size={14} /><span>{activeFile.path.split("/").pop()}</span>{activeFile.dirty && <i /> }<button title="Close file" onClick={() => setActiveFile(null)}><X size={14} /></button><button className="save-file-button" onClick={() => void saveFile()} disabled={!activeFile.dirty || busy}><Save size={14} /> Save</button></div>
          {activeFile.path.match(/\.(png|jpe?g|gif|webp)$/i) ? <div className="workspace-preview"><img className="workspace-image-preview" src={`${API_BASE}/api/workspace/asset?path=${encodeURIComponent(activeFile.path)}`} alt={activeFile.path.split("/").pop()} /><p>Local image preview · ready for a future agent attachment flow</p></div> :
          <textarea className="workspace-code-editor" spellCheck={false} value={activeFile.content} onChange={(event) => setActiveFile({ ...activeFile, content: event.target.value, dirty: true })} />}
        </> : <div className="workspace-welcome"><HardDrive size={32} /><strong>Local workspace</strong><p>Open a file, create a folder, or upload files to begin.</p><span>File operations stay inside the configured workspace directory.</span></div>}
      </div>
    </div>
    {message && <div className="workspace-message" role="status">{message}</div>}
  </section>;
}
