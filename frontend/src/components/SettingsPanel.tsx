import { useCallback, useEffect, useState } from "react";
import { Check, KeyRound, RefreshCw, Save, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "../services/api";
import { useTranslation } from "../i18n";

type SecretName = "kaggle-key" | "tunnel-password" | "openai-compatible-api-key";
type SecretStatus = Record<SecretName, boolean>;
const SECRET_FIELDS: { name: SecretName; titleKey: string; detailKey: string }[] = [
  { name: "kaggle-key", titleKey: "settings.kaggleKey", detailKey: "settings.kaggleKeyHelp" },
  { name: "tunnel-password", titleKey: "settings.tunnelPassword", detailKey: "settings.tunnelPasswordHelp" },
  { name: "openai-compatible-api-key", titleKey: "settings.openaiKey", detailKey: "settings.openaiKeyHelp" },
];

export default function SettingsPanel() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<SecretStatus | null>(null);
  const [values, setValues] = useState<Record<SecretName, string>>({
    "kaggle-key": "", "tunnel-password": "", "openai-compatible-api-key": "",
  });
  const [busy, setBusy] = useState<SecretName | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try { setStatus(await api.getSecretStatus()); }
    catch (e) { setError(e instanceof Error ? e.message : t("settings.credentialsLoadError")); }
    finally { setLoading(false); }
  }, [t]);

  useEffect(() => { void refresh(); }, [refresh]);

  const save = async (name: SecretName) => {
    const value = values[name].trim();
    if (!value) { setError(t("settings.enterCredential")); return; }
    setBusy(name); setError(""); setMessage("");
    try {
      await api.saveSecret(name, value);
      setValues((current) => ({ ...current, [name]: "" }));
      setMessage(t("settings.credentialSaved"));
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : t("settings.credentialSaveError")); }
    finally { setBusy(null); }
  };

  const remove = async (name: SecretName) => {
    setBusy(name); setError(""); setMessage("");
    try {
      await api.deleteSecret(name);
      setMessage(t("settings.credentialDeleted"));
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : t("settings.credentialDeleteError")); }
    finally { setBusy(null); }
  };

  return <div className="settings-page">
    <section className="panel credentials-panel">
      <div className="panel-header"><div><h2>{t("settings.credentialsTitle")}</h2><p>{t("settings.credentialsSubtitle")}</p></div><KeyRound size={18} className="panel-muted-icon" /></div>
      <div className="credentials-intro"><ShieldCheck size={16} /><span>{t("settings.credentialsSecurityNote")}</span></div>
      <div className="credentials-list">
        {SECRET_FIELDS.map(({ name, titleKey, detailKey }) => <article className="credential-row" key={name}>
          <div className="credential-copy"><strong>{t(titleKey as never)}</strong><p>{t(detailKey as never)}</p><span className={status?.[name] ? "credential-state is-set" : "credential-state"}>{loading ? t("settings.checkingCredential") : status?.[name] ? t("settings.credentialConfigured") : t("settings.credentialMissing")}</span></div>
          <div className="credential-controls">
            <input type="password" autoComplete="new-password" spellCheck={false} value={values[name]} onChange={(event) => setValues((current) => ({ ...current, [name]: event.target.value }))} placeholder={t("settings.secretPlaceholder")} aria-label={t(titleKey as never)} />
            <div className="credential-actions">
              <button className="primary-button" onClick={() => void save(name)} disabled={loading || busy !== null || !values[name].trim()}><Save size={14} />{busy === name ? t("actions.saving") : t("actions.save")}</button>
              <button className="workspace-icon-btn" onClick={() => void remove(name)} disabled={loading || busy !== null || !status?.[name]} title={t("settings.deleteCredential")} aria-label={t("settings.deleteCredential")}><Trash2 size={15} /></button>
            </div>
          </div>
        </article>)}
      </div>
      <div className="credentials-footer"><span>{t("settings.environmentPriority")}</span><button className="workspace-icon-btn" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14} className={loading ? "spin" : ""} /> {t("actions.refresh")}</button></div>
      {error && <div className="error-banner credentials-message">{error}</div>}
      {message && <div className="credentials-success"><Check size={14} />{message}</div>}
    </section>
    <div className="provider-footnote"><ShieldCheck size={14} />{t("settings.restartNote")}</div>
  </div>;
}
