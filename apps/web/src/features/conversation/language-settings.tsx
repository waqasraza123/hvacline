"use client";

import { useEffect, useState } from "react";
import { LANGUAGE_NAMES, parseVoiceLanguageRegistry, type LanguageCode, type VoiceChannel, type VoiceLanguageConfiguration, type VoiceLanguageRegistry } from "@insurance-operations/customer-core";
import { requestApi } from "../operations/api";
import styles from "./multilingual.module.css";

const CHANNEL_LABELS: Record<VoiceChannel, string> = { browser: "Browser", mobile: "Mobile", phone: "Inbound phone", recovery: "Lead recovery" };
const CHANNELS = Object.keys(CHANNEL_LABELS) as VoiceChannel[];
const CODES = Object.keys(LANGUAGE_NAMES) as LanguageCode[];
const DEFAULT: VoiceLanguageConfiguration = { default_language: "en", enabled_languages: ["en"], automatic_switching: false, presets: {} };

export function LanguageSettings({ apiBaseUrl, adminToken }: { apiBaseUrl: string; adminToken?: string }) {
  const [registry, setRegistry] = useState<VoiceLanguageRegistry>();
  const [draft, setDraft] = useState<VoiceLanguageConfiguration>(DEFAULT);
  const [channel, setChannel] = useState<VoiceChannel>("browser");
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const api = async (method = "GET", body?: unknown) => parseVoiceLanguageRegistry(await requestApi<unknown>(apiBaseUrl, adminToken ?? "", "voice-languages", method, body));
  useEffect(() => {
    let active = true;
    void requestApi<unknown>(apiBaseUrl, adminToken ?? "", "voice-languages").then((raw) => {
      const value = parseVoiceLanguageRegistry(raw);
      if (active) { setRegistry(value); setDraft(value.configuration); }
    }).catch((error: unknown) => { if (active) setMessage(error instanceof Error ? error.message : "Language settings could not be loaded."); });
    return () => { active = false; };
  }, [apiBaseUrl, adminToken]);
  async function save() {
    if (!registry || busy) return;
    setBusy(true); setMessage("");
    try {
      const value = await api("PUT", { ...draft, expected_row_version: registry.row_version });
      setRegistry(value); setDraft(value.configuration);
      setMessage("Settings saved. Hosted agents were not changed. Review Requires Provider Setup below before live use.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Settings could not be saved."); }
    finally { setBusy(false); }
  }
  function preset(code: LanguageCode, field: "voice_id" | "greeting", value: string) {
    setDraft({ ...draft, presets: { ...draft.presets, [channel]: { ...draft.presets[channel],
      [code]: { voice_id: "", greeting: "", ...draft.presets[channel]?.[code], [field]: value } } } });
  }
  return <section className={`${styles.root} settings-card`} aria-labelledby="voice-language-settings">
    <p className="section-kicker">Languages &amp; Voice</p>
    <h2 id="voice-language-settings">Let customers choose how to speak.</h2>
    <p>Save your preferred languages, voices and greetings here. Server-side, agency-bound provider verification determines live availability. Phone and recovery multilingual workflows require further adapter support.</p>
    <div className={styles.controls}>
      <label>Default language<select disabled={busy} value={draft.default_language} onChange={(event) => setDraft({ ...draft, default_language: event.target.value as LanguageCode })}>
        {draft.enabled_languages.map((code) => <option key={code} value={code}>{LANGUAGE_NAMES[code]}</option>)}
      </select></label>
      <label><input type="checkbox" disabled={busy} checked={draft.automatic_switching} onChange={(event) => setDraft({ ...draft, automatic_switching: event.target.checked })} /> Enable provider language detection and switching</label>
    </div>
    <fieldset disabled={busy}><legend>Languages to configure</legend><div className={styles.controls}>
      {CODES.map((code) => <label key={code}><input type="checkbox" checked={draft.enabled_languages.includes(code)} disabled={code === "en"}
        onChange={(event) => setDraft({ ...draft, default_language: !event.target.checked && draft.default_language === code ? "en" : draft.default_language,
          enabled_languages: event.target.checked ? [...draft.enabled_languages, code] : draft.enabled_languages.filter((item) => item !== code) })} /> {LANGUAGE_NAMES[code]}{code === "ur" ? " · requires complete stack verification" : ""}</label>)}
    </div></fieldset>
    <label>Agent/channel<select value={channel} disabled={busy} onChange={(event) => setChannel(event.target.value as VoiceChannel)}>
      {CHANNELS.map((item) => <option value={item} key={item}>{CHANNEL_LABELS[item]}</option>)}
    </select></label>
    <div className={styles.presetGrid}>{draft.enabled_languages.map((code) => <fieldset key={code} disabled={busy}>
      <legend>{LANGUAGE_NAMES[code]}</legend>
      <label>Configured voice ID<input value={draft.presets[channel]?.[code]?.voice_id ?? ""} maxLength={200} onChange={(event) => preset(code, "voice_id", event.target.value)} autoComplete="off" /></label>
      <label>Reviewed greeting and AI disclosure<textarea dir={code === "ar" || code === "ur" ? "rtl" : "auto"} lang={code} maxLength={600} value={draft.presets[channel]?.[code]?.greeting ?? ""} onChange={(event) => preset(code, "greeting", event.target.value)} /></label>
    </fieldset>)}</div>
    <div className={styles.controls}>
      <button className="primary-button" disabled={busy || !registry || registry.row_version < 1} type="button" onClick={() => void save()}>{busy ? "Saving…" : "Save Languages & Voice"}</button>
      <button type="button" disabled={busy} onClick={() => { setDraft(DEFAULT); setMessage("English-only default selected. Save to persist; any hosted multilingual setup must also be reverted before live use."); }}>Restore English-only default</button>
      <button type="button" disabled={busy} onClick={() => { setBusy(true); void api().then((value) => { setRegistry(value); setDraft(value.configuration); setMessage(""); }).catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Reload failed.")).finally(() => setBusy(false)); }}>Reload saved settings</button>
    </div>
    {message && <p role="status">{message}</p>}
    {registry?.row_version === 0 && <p>Save the business profile above before saving language settings.</p>}
    {registry && <>
      <h3>Saved configuration · channel compatibility</h3>
      <p>Effective starting language: browser {registry.effective_defaults.browser ? LANGUAGE_NAMES[registry.effective_defaults.browser] : "unavailable"}, mobile {registry.effective_defaults.mobile ? LANGUAGE_NAMES[registry.effective_defaults.mobile] : "unavailable"}. Pending settings keep existing English behavior until verified.</p>
      <div className={styles.tableWrap}><table><caption>Server-authoritative language availability</caption><thead><tr><th>Language</th>{CHANNELS.map((item) => <th key={item}>{CHANNEL_LABELS[item]}</th>)}</tr></thead><tbody>
        {CODES.map((code) => <tr key={code}><th>{LANGUAGE_NAMES[code]}</th>{CHANNELS.map((item) => {
          const row = registry.languages.find((entry) => entry.code === code && entry.channel === item);
          return <td key={item}>{row?.status === "existing_english_default" ? "Existing English default · runtime UNVERIFIED" : row?.available ? "Verified configuration" : row?.status === "unsupported" ? "Unsupported" : "Requires Provider Setup"}</td>;
        })}</tr>)}
      </tbody></table></div>
      <details><summary>Exact provider setup required</summary><ol>
        <li>Use each channel’s existing private agent. Set the primary language and Additional Languages to the saved list exactly.</li>
        <li>Match each language’s voice ID and reviewed first message above. Check ASR, LLM and TTS compatibility, disclosure, retention and duration.</li>
        <li>For browser/mobile enable only the language session override in Security, retaining the existing text-only override and booking tools.</li>
        <li>If switching is enabled, add the language_detection system tool and disable Only at start of conversation. Apply the safety instructions in docs/multilingual-voice.md.</li>
        <li>Enable agent_tool_request and agent_tool_response_full_payload client events. Requests invalidate pending readbacks; only a complete successful language result updates the live language display.</li>
        <li>Extend the existing prepare/reserve/confirm client-tool schemas with optional readback_language. Review the exact code list in docs/elevenlabs-browser-tools.json.</li>
        <li>After owner acceptance, record server-only VOICE_LANGUAGE_PROVIDER_EVIDENCE for each agency/agent/channel. Local saves never edit or attest hosted configuration.</li>
      </ol><p>Phone and recovery remain unsupported for additional languages even if evidence is supplied. English-only restore also requires matching hosted settings and removal of stale evidence.</p></details>
      <h3>Language diagnostics · actual usage</h3><p>{registry.note}</p>
      <p>Observed switches: unavailable · switch failures: unavailable · unsupported-language requests: unavailable. Translation accuracy and fluency are not measured.</p>
      <div className={styles.tableWrap}><table><caption>Up to 100 latest agency sessions · no transcripts or customer details</caption><thead><tr><th>Initial language</th><th>Session outcome</th><th>Booking outcome</th><th>Failure</th></tr></thead><tbody>
        {registry.diagnostics?.map((item, index) => <tr key={index}><td>{LANGUAGE_NAMES[item.initial_language]}</td><td>{item.outcome}</td><td>{item.booking_outcome.replaceAll("_", " ")}</td><td>{item.failure_code ?? "None recorded"}</td></tr>)}
      </tbody></table>{!registry.diagnostics?.length && <p>No actual session metadata loaded. Demo activity never enters these metrics.</p>}</div>
    </>}
  </section>;
}
