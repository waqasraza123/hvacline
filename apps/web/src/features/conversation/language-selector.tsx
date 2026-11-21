"use client";

import { useEffect, useState } from "react";
import { LANGUAGE_NAMES, parseVoiceLanguageRegistry, type LanguageCode, type VoiceLanguageRegistry } from "@insurance-operations/customer-core";
import { requestApi } from "../operations/api";

export function useVoiceLanguages(apiBaseUrl: string, adminToken?: string) {
  const [registry, setRegistry] = useState<VoiceLanguageRegistry>();
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [languageError, setError] = useState("");
  useEffect(() => {
    let active = true;
    void requestApi<unknown>(apiBaseUrl, adminToken ?? "", "voice-languages").then((raw) => {
      const value = parseVoiceLanguageRegistry(raw);
      if (!active) return;
      setRegistry(value);
      setLanguage(value.effective_defaults.browser ?? "en");
      setError("");
    }).catch(() => {
      if (active) setError("Language settings could not be loaded. Refresh before starting.");
    });
    return () => { active = false; };
  }, [apiBaseUrl, adminToken]);
  return { registry, language, setLanguage, languageError };
}

export function LanguageSelector({ registry, language, onChange, disabled, error, observedLanguage, switchFailed, live }: {
  registry?: VoiceLanguageRegistry; language: LanguageCode; onChange: (value: LanguageCode) => void;
  disabled: boolean; error: string;
  observedLanguage?: LanguageCode; switchFailed?: boolean;
  live?: boolean;
}) {
  const languages = registry?.languages.filter((item) => item.channel === "browser" && item.available) ?? [];
  return <div className="receptionist-context">
    <label>Conversation language
      <select aria-label="Conversation language" value={language} disabled={disabled || !registry}
        onChange={(event) => onChange(event.target.value as LanguageCode)}>
        {!languages.length && <option value={language}>{LANGUAGE_NAMES[language]} · Requires Provider Setup</option>}
        {languages.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
      </select>
    </label>
    {disabled && <p role="status">{observedLanguage ? `${live ? "Active" : "Last observed"} language: ${LANGUAGE_NAMES[observedLanguage]} · provider result observed.` : `Initial language: ${LANGUAGE_NAMES[language]}.${live ? " Current language is not confirmed by a provider result." : ""}`}</p>}
    {disabled && switchFailed && <p role="status">The provider could not confirm a language switch. Continue in the current language or ask for staff assistance.</p>}
    {!disabled && <p>Only configured languages are available. Ask Line to change language during a conversation when provider switching is enabled. Otherwise, ask for staff assistance.</p>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
