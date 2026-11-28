export const EXTERNAL_FAILURES_HEADER = "X-External-Failures";
export const externalProviders = {
  elevenlabs: "ElevenLabs", stripe: "Stripe", google_calendar: "Google Calendar",
  gohighlevel: "GoHighLevel", resend: "Resend", telnyx: "Telnyx", twilio: "Twilio",
  openai: "OpenAI", openai_compatible: "AI provider", ollama: "Local AI model",
} as const;
export type ExternalProvider = keyof typeof externalProviders;
export const externalFailureKinds = ["billing", "access", "rate_limited", "timeout", "unavailable", "rejected"] as const;
export type ExternalFailureKind = (typeof externalFailureKinds)[number];
export type ExternalFailure = { provider: ExternalProvider; kind: ExternalFailureKind };

const savedFailureCodes: Record<string, ExternalFailure> = {
  STRIPE_UNAVAILABLE: { provider: "stripe", kind: "unavailable" },
  STRIPE_RESPONSE_INVALID: { provider: "stripe", kind: "rejected" },
  EMAIL_RESPONSE_UNKNOWN: { provider: "resend", kind: "unavailable" },
  EMAIL_IDEMPOTENCY_CONFLICT: { provider: "resend", kind: "rejected" },
  GHL_AUTH_REQUIRED: { provider: "gohighlevel", kind: "access" },
  GHL_RATE_LIMITED: { provider: "gohighlevel", kind: "rate_limited" },
  GHL_TEMPORARILY_UNAVAILABLE: { provider: "gohighlevel", kind: "unavailable" },
  GHL_NETWORK_UNAVAILABLE: { provider: "gohighlevel", kind: "unavailable" },
  GHL_REQUEST_REJECTED: { provider: "gohighlevel", kind: "rejected" },
  GHL_RESPONSE_INVALID: { provider: "gohighlevel", kind: "unavailable" },
  AI_CONNECTION_REJECTED: { provider: "openai_compatible", kind: "rejected" },
  AI_CONNECTION_FAILED: { provider: "openai_compatible", kind: "unavailable" },
  AI_DNS_FAILED: { provider: "openai_compatible", kind: "unavailable" },
};

export function parseExternalFailures(value: unknown): ExternalFailure[] {
  const failures = new Map<string, ExternalFailure>();
  const legacyFailures = new Map<string, ExternalFailure>();
  function visit(item: unknown, depth: number) {
    if (depth > 8 || failures.size >= 8) return;
    if (typeof item === "string") {
      const saved = Object.hasOwn(savedFailureCodes, item) ? savedFailureCodes[item] : undefined;
      if (saved) { legacyFailures.set(saved.provider, saved); return; }
      for (const provider of Object.keys(externalProviders) as ExternalProvider[]) {
        for (const kind of externalFailureKinds) {
          if (item === `EXTERNAL_${provider.toUpperCase()}_${kind.toUpperCase()}`) {
            failures.set(`${provider}:${kind}`, { provider, kind });
          }
        }
      }
      return;
    }
    if (Array.isArray(item)) { item.slice(0, 100).forEach((child) => visit(child, depth + 1)); return; }
    if (typeof item !== "object" || item === null) return;
    const record = item as Record<string, unknown>;
    if (typeof record.provider === "string" && Object.hasOwn(externalProviders, record.provider) &&
      externalFailureKinds.some((kind) => kind === record.kind)) {
      const failure = { provider: record.provider, kind: record.kind } as ExternalFailure;
      failures.set(`${failure.provider}:${failure.kind}`, failure);
    }
    for (const key of ["external_failures", "error", "details", "code", "failure_code", "last_error", "recent", "items", "attempts", "continuations", "connection", "connections", "notifications", "sync"]) {
      visit(record[key], depth + 1);
    }
  }
  visit(value, 0);
  const providers = new Set([...failures.values()].map((failure) => failure.provider));
  return [...failures.values(), ...[...legacyFailures.values()].filter(
    (failure) => !providers.has(failure.provider),
  )].slice(0, 8);
}

export function externalFailureMessage({ provider, kind }: ExternalFailure): string {
  const name = externalProviders[provider];
  switch (kind) {
    case "billing": return `${name} could not complete the request because of its account balance or billing limit. Review the provider's billing settings before trying again.`;
    case "access": return `${name} denied access. Ask the account owner to check the connection, credentials and permissions.`;
    case "rate_limited": return `${name} has reached a request or usage limit. Please wait before trying again.`;
    case "timeout": return `${name} took too long to respond. Check the saved status before repeating the action.`;
    case "unavailable": return `${name} is temporarily unavailable. Check the saved status before trying again later.`;
    case "rejected": return `${name} could not accept this request. Review the connection and request details before trying again.`;
  }
}

export function externalFailureHeaders(response: Response): Record<string, string> {
  const value = response.headers.get(EXTERNAL_FAILURES_HEADER);
  if (!value || value.length > 4096) return {};
  try {
    const failures = parseExternalFailures(JSON.parse(value));
    return failures.length ? { [EXTERNAL_FAILURES_HEADER]: JSON.stringify(failures) } : {};
  } catch { return {}; }
}
