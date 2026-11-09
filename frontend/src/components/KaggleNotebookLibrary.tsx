import { useState, type FormEvent } from "react";
import { Download, Search } from "lucide-react";
import { api } from "../services/api";
import type { KaggleNotebookItem } from "../types/kaggle";
import { useTranslation } from "../i18n";

export default function KaggleNotebookLibrary() {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<KaggleNotebookItem[]>([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (nextPage = 1) => {
    if (query.trim().length < 2 || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.searchKaggleNotebooks(query.trim(), nextPage);
      setItems(result.items);
      setPage(result.page);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("kaggle.unknownError"));
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void search(1);
  };

  return (
    <section className="panel kaggle-panel">
      <div className="panel-header">
        <div><h2>{t("kaggle.libraryTitle")}</h2><p>{t("kaggle.librarySubtitle")}</p></div>
        <Search size={18} className="panel-muted-icon" />
      </div>
      <div className="kaggle-body">
        <form className="kaggle-field" onSubmit={submit}>
          <span>{t("kaggle.search")}</span>
          <div className="kaggle-actions">
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("kaggle.searchPlaceholder")} maxLength={120} minLength={2} />
            <button className="primary-button" type="submit" disabled={busy || query.trim().length < 2}>
              <Search size={15} />{busy ? t("kaggle.searching") : t("kaggle.search")}
            </button>
          </div>
        </form>
        {error && <div className="error-banner kaggle-error">{error}</div>}
        {searched && items.length === 0 && !busy && <p className="kaggle-msg">{t("kaggle.noResults")}</p>}
        {items.map((item) => (
          <div className="detail-row" key={item.ref}>
            <div>
              <strong>{item.title}</strong>
              <div className="kaggle-msg">{item.ref} · {item.votes} votes {item.last_run ? `· ${item.last_run}` : ""}</div>
            </div>
            <a className="secondary-button" href={`/api/kaggle/notebooks/${encodeURIComponent(item.ref.split("/")[0])}/${encodeURIComponent(item.ref.split("/")[1])}/download`}>
              <Download size={14} />{t("kaggle.download")}
            </a>
          </div>
        ))}
        {searched && <div className="kaggle-actions">
          <button className="secondary-button" disabled={busy || page <= 1} onClick={() => void search(page - 1)}>{t("kaggle.previous")}</button>
          <button className="secondary-button" disabled={busy || items.length === 0 || page >= 100} onClick={() => void search(page + 1)}>{t("kaggle.next")}</button>
        </div>}
        <p className="kaggle-msg">{t("kaggle.downloadNote")}</p>
      </div>
    </section>
  );
}
