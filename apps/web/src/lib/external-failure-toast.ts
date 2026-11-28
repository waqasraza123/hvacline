"use client";

import { toast } from "sonner";
import { ELEVENLABS_CREDITS_MESSAGE, isElevenLabsAccountRestriction } from "./elevenlabs-errors";
import { externalFailureMessage, parseExternalFailures } from "./external-failures";

export function notifyExternalFailures(value: unknown) {
  const elevenLabsRestricted = isElevenLabsAccountRestriction(value);
  if (elevenLabsRestricted) toast.error(ELEVENLABS_CREDITS_MESSAGE, {
    id: "elevenlabs-account-restricted", duration: 10000, closeButton: true,
  });
  for (const failure of parseExternalFailures(value)) {
    if (elevenLabsRestricted && failure.provider === "elevenlabs" && ["billing", "access"].includes(failure.kind)) continue;
    toast.error(externalFailureMessage(failure), {
      id: `external-${failure.provider}-${failure.kind}`, duration: 10000, closeButton: true,
    });
  }
}
