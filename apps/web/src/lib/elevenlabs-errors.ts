export const ELEVENLABS_ACCOUNT_RESTRICTED = "ELEVENLABS_ACCOUNT_RESTRICTED";
export const ELEVENLABS_CREDITS_MESSAGE = "Our agents were about to respond, but we detected that your ElevenLabs credits are 0. Refill your balance to try again.";

const restrictionCodes = new Set([
  "insufficient_credits", "quota_exceeded", "payment_required", "payment_failed",
  "payment_not_verified", "payment_not_successful", "subscription_required",
  "account_restricted", "account_suspended", "access_restricted", "access_denied",
  "workspace_access_denied", "model_access_denied", "voice_access_denied",
  "authorization_error", "feature_not_available", "paid_plan_required", "detected_unusual_activity",
]);
const restrictionCodePattern = new RegExp(`\\b(${[...restrictionCodes].join("|")})\\b`, "i");
const restrictionMessage = /(?:insufficient|not enough|no remaining|out of) (?:credits|quota)|(?:credits|quota) (?:exhausted|exceeded|depleted)|payment (?:failed|declined|not (?:verified|successful)|required)|(?:account|access) (?:is |has been )?(?:restricted|denied|blocked|suspended)|\b(?:status(?: code)?[: =]*|HTTP[ /])(?:402|403)\b/i;

export function isElevenLabsAccountRestriction(value: unknown, source: "api" | "sdk" = "api", depth = 0): boolean {
  if (depth > 4) return false;
  if (typeof value === "string") {
    if (value === ELEVENLABS_ACCOUNT_RESTRICTED) return true;
    if (source !== "sdk") return false;
    const bounded = value.slice(0, 8000);
    if (restrictionCodePattern.test(bounded) || restrictionMessage.test(bounded)) return true;
    try { return isElevenLabsAccountRestriction(JSON.parse(bounded), source, depth + 1); }
    catch { return false; }
  }
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return ["error", "details", "provider_error_code", "detail", "code", "status", "type", "message", "reason", "closeReason", "context", "error_event"].some(
    (key) => isElevenLabsAccountRestriction(record[key], source, depth + 1),
  );
}

export function elevenLabsErrorDetails(value: unknown): { provider_error_code?: typeof ELEVENLABS_ACCOUNT_RESTRICTED } {
  return isElevenLabsAccountRestriction(value) ? { provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED } : {};
}
