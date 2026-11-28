"use client";

import { notifyExternalFailures } from "./external-failure-toast";
import type { ExternalFailureKind } from "./external-failures";
import { toast } from "sonner";
import { ELEVENLABS_CREDITS_MESSAGE, isElevenLabsAccountRestriction } from "./elevenlabs-errors";

export function notifyElevenLabsError(value: unknown, source: "api" | "sdk" = "api") {
  if (!isElevenLabsAccountRestriction(value, source)) {
    if (source === "sdk" && value) {
      const item = typeof value === "object" ? value as Record<string, unknown> : { message: value };
      if (item.reason === "user" || item.reason === "agent") return false;
      const message = [item.message, item.closeReason,
        typeof item.context === "object" && item.context !== null ? (item.context as Record<string, unknown>).reason : undefined,
      ].filter((part): part is string => typeof part === "string").join(" ").slice(0, 8000);
      if ((message || item.reason === "error") && !/microphone|permission denied|notallowederror|notfounderror|audio device/i.test(message)) {
        const kind: ExternalFailureKind = /rate.limit|concurrent.limit|429/i.test(message) ? "rate_limited"
          : /invalid.api.key|401|unauthorized/i.test(message) ? "access"
          : /timed? ?out|timeout/i.test(message) ? "timeout" : "unavailable";
        notifyExternalFailures({ external_failures: [{ provider: "elevenlabs", kind }] });
      }
    }
    return false;
  }
  toast.error(ELEVENLABS_CREDITS_MESSAGE, {
    id: "elevenlabs-account-restricted",
    duration: 10000,
    closeButton: true,
  });
  return true;
}
