export const LANGUAGE_NAMES = {
  en: "English", es: "Spanish", fr: "French", ar: "Arabic",
  hi: "Hindi", zh: "Mandarin Chinese", ur: "Urdu",
} as const;
export type LanguageCode = keyof typeof LANGUAGE_NAMES;
export type VoiceChannel = "browser" | "mobile" | "phone" | "recovery";
export type LanguagePreset = { voice_id: string; greeting: string };
export type VoiceLanguageConfiguration = {
  default_language: LanguageCode;
  enabled_languages: LanguageCode[];
  automatic_switching: boolean;
  presets: Partial<Record<VoiceChannel, Partial<Record<LanguageCode, LanguagePreset>>>>;
};
export type VoiceLanguageSession = Readonly<{
  language: LanguageCode;
  allowed_languages: readonly LanguageCode[];
  automatic_switching: boolean;
  overrides: { agent: { language: LanguageCode } } | null;
}>;
export type LanguageCapability = {
  channel: VoiceChannel; code: LanguageCode; name: string; enabled: boolean;
  available: boolean; voice_id: string; greeting: string; automatic_switching: boolean;
  status: "existing_english_default" | "verified_configuration" | "requires_provider_setup" | "unsupported";
  verified_at: string | null;
};
export type VoiceLanguageRegistry = {
  effective_defaults: Record<VoiceChannel, LanguageCode | null>;
  configuration: VoiceLanguageConfiguration;
  languages: LanguageCapability[];
  row_version: number;
  observation_status: "unavailable";
  observed_switches: null; switch_failures: null; unsupported_requests: null;
  note: string;
  diagnostics?: { initial_language: LanguageCode; outcome: string; failure_code: string | null; booking_outcome: string; source: "actual_session" }[];
};
export function isLanguageCode(value: unknown): value is LanguageCode {
  return typeof value === "string" && Object.hasOwn(LANGUAGE_NAMES, value);
}
export function parseVoiceLanguageSession(value: unknown): VoiceLanguageSession | undefined {
  if (value == null) return undefined;
  if (typeof value !== "object") throw new Error("Invalid voice language authorization.");
  const data = value as Record<string, unknown>;
  if (!isLanguageCode(data.language) || !Array.isArray(data.allowed_languages) ||
      !data.allowed_languages.every(isLanguageCode) || !data.allowed_languages.includes(data.language) ||
      data.allowed_languages.length > 7 || new Set(data.allowed_languages).size !== data.allowed_languages.length ||
      typeof data.automatic_switching !== "boolean") throw new Error("Invalid voice language authorization.");
  const overrides = data.overrides;
  if (overrides !== null && (typeof overrides !== "object" || !overrides ||
      !("agent" in overrides) || typeof overrides.agent !== "object" || !overrides.agent ||
      !("language" in overrides.agent) || overrides.agent.language !== data.language))
    throw new Error("Invalid voice language override.");
  return { language: data.language, allowed_languages: data.allowed_languages,
    automatic_switching: data.automatic_switching, overrides: overrides === null ? null : { agent: { language: data.language } } };
}
export function languageSessionOverrides(value?: VoiceLanguageSession) {
  return value?.overrides ? { overrides: value.overrides } : {};
}

export function parseVoiceLanguageRegistry(value: unknown): VoiceLanguageRegistry {
  const isRecord = (item: unknown): item is Record<string, unknown> => !!item && typeof item === "object" && !Array.isArray(item);
  const channels: readonly string[] = ["browser", "mobile", "phone", "recovery"];
  if (!isRecord(value) || !isRecord(value.configuration) || !Array.isArray(value.languages) ||
      !Number.isSafeInteger(value.row_version) || !isRecord(value.effective_defaults)) throw new Error("Invalid voice language settings.");
  const config = value.configuration;
  const defaults = value.effective_defaults;
  if (!isLanguageCode(config.default_language) || !Array.isArray(config.enabled_languages) ||
      !config.enabled_languages.every(isLanguageCode) || !config.enabled_languages.includes(config.default_language) ||
      !config.enabled_languages.includes("en") || typeof config.automatic_switching !== "boolean" || !isRecord(config.presets))
    throw new Error("Invalid voice language settings.");
  for (const [channel, presets] of Object.entries(config.presets)) {
    if (!channels.includes(channel) || !isRecord(presets)) throw new Error("Invalid voice presets.");
    for (const [code, preset] of Object.entries(presets)) {
      if (!isLanguageCode(code) || !isRecord(preset) || typeof preset.voice_id !== "string" || typeof preset.greeting !== "string") throw new Error("Invalid voice preset.");
    }
  }
  const identities = new Set<string>();
  for (const row of value.languages) {
    if (!isRecord(row) || !isLanguageCode(row.code) || typeof row.channel !== "string" || !channels.includes(row.channel) ||
        typeof row.name !== "string" || typeof row.available !== "boolean" || typeof row.enabled !== "boolean" ||
        typeof row.automatic_switching !== "boolean" || typeof row.voice_id !== "string" || typeof row.greeting !== "string" ||
        !["existing_english_default", "verified_configuration", "requires_provider_setup", "unsupported"].includes(String(row.status)) ||
        (row.verified_at !== null && typeof row.verified_at !== "string")) throw new Error("Invalid voice capability.");
    identities.add(`${row.channel}:${row.code}`);
  }
  const capabilityCount = Object.keys(LANGUAGE_NAMES).length * channels.length;
  if (identities.size !== capabilityCount || value.languages.length !== capabilityCount ||
      channels.some((channel) => defaults[channel] !== null && !isLanguageCode(defaults[channel])))
    throw new Error("Incomplete voice language capabilities.");
  if (value.observation_status !== "unavailable" || value.observed_switches !== null || value.switch_failures !== null ||
      value.unsupported_requests !== null || typeof value.note !== "string") throw new Error("Invalid language diagnostics.");
  if (value.diagnostics !== undefined && (!Array.isArray(value.diagnostics) || !value.diagnostics.every((row) => isRecord(row) &&
      isLanguageCode(row.initial_language) && typeof row.outcome === "string" && typeof row.booking_outcome === "string" &&
      (row.failure_code === null || typeof row.failure_code === "string") && row.source === "actual_session"))) throw new Error("Invalid session diagnostics.");
  return value as unknown as VoiceLanguageRegistry;
}

export type ObservedLanguageResult = { kind: "switched"; language: LanguageCode } | { kind: "failed" | "unobserved" };
export class ProviderLanguageObserver {
  private session?: VoiceLanguageSession;
  private seen = new Set<string>();
  start(session?: VoiceLanguageSession) { this.session = session; this.seen.clear(); }
  receive(value: unknown): ObservedLanguageResult | undefined {
    if (!this.session || typeof value !== "object" || !value) return;
    const event = value as Record<string, unknown>;
    if (event.tool_name !== "language_detection" || event.tool_type !== "system" ||
        typeof event.tool_call_id !== "string" || event.tool_call_id.length > 200) return;
    if (!this.session.automatic_switching) return { kind: "failed" };
    if (event.is_error === true || event.is_blocked === true || event.is_called === false) {
      const key = `failed:${event.tool_call_id}`;
      if (this.seen.has(key)) return;
      this.seen.add(key);
      return { kind: "failed" };
    }
    if (this.seen.has(`success:${event.tool_call_id}`)) return;
    if (event.is_error !== false || event.is_called !== true || event.truncated === true ||
        typeof event.full_tool_result !== "string" || event.full_tool_result.length > 4096) return { kind: "unobserved" };
    try {
      const result: unknown = JSON.parse(event.full_tool_result);
      if (!result || typeof result !== "object" || !("language" in result) || !isLanguageCode(result.language)) return { kind: "unobserved" };
      if (("status" in result && result.status !== "success") || !this.session.allowed_languages.includes(result.language)) return { kind: "failed" };
      const key = `success:${event.tool_call_id}`;
      if (this.seen.has(key)) return;
      this.seen.add(key);
      return { kind: "switched", language: result.language };
    } catch { return { kind: "unobserved" }; }
  }
}
