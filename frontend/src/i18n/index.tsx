import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { en } from "./locales/en";
import { uz } from "./locales/uz";

export type Language = "uz" | "en";
type TranslationKey = keyof typeof uz;
type LanguageContextValue = { language: Language; setLanguage: (language: Language) => void; t: (key: TranslationKey) => string };
const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    try { return window.localStorage.getItem("nexus-language") === "en" ? "en" : "uz"; } catch { return "uz"; }
  });
  const setLanguage = (next: Language) => {
    setLanguageState(next);
    try { window.localStorage.setItem("nexus-language", next); } catch { /* Storage may be unavailable in restricted webviews. */ }
  };
  const value = useMemo<LanguageContextValue>(() => ({ language, setLanguage, t: (key) => (language === "uz" ? uz : en)[key] }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useTranslation() {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useTranslation must be used inside LanguageProvider");
  return value;
}
