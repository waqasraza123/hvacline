import { expect, it, vi } from "vitest";
import { toast } from "sonner";
import { ELEVENLABS_ACCOUNT_RESTRICTED, ELEVENLABS_CREDITS_MESSAGE, elevenLabsErrorDetails, isElevenLabsAccountRestriction } from "./elevenlabs-errors";
import { notifyElevenLabsError } from "./elevenlabs-toast";

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

it.each([
  { error: { details: { provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED } } },
  { provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED },
])("recognizes only the safe provider marker on application responses", (payload) => {
  expect(isElevenLabsAccountRestriction(payload)).toBe(true);
  expect(elevenLabsErrorDetails(payload)).toEqual({ provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED });
});

it.each([
  "quota_exceeded",
  "ElevenLabs rejected this session: insufficient_credits",
  { message: "Payment not successful" },
  { reason: "error", context: { reason: "Account is restricted" } },
  { closeReason: '{"detail":{"status":"payment_required"}}' },
  new Error("Request failed with status code 403"),
])("recognizes SDK billing and access failures %j", (failure) => {
  expect(isElevenLabsAccountRestriction(failure, "sdk")).toBe(true);
});

it.each([
  { error: { code: "AUTHENTICATION_REQUIRED", status: 401 } },
  { error: { code: "FORBIDDEN", status: 403 } },
  { error: { message: "Access denied" } },
  { error: { code: "HOMEPAGE_SIGN_IN_REQUIRED" } },
  { error: { code: "DEMO_CALL_LIMIT", details: { remaining: 0 } } },
  new Error("Network connection timed out"),
])("keeps unrelated application failures out of the credit toast", (failure) => {
  expect(isElevenLabsAccountRestriction(failure)).toBe(false);
  expect(elevenLabsErrorDetails(failure)).toEqual({});
});

it.each(["rate_limit_exceeded", "concurrent_limit_exceeded", "invalid_api_key", "HTTP status: 500", "Microphone permission denied"])(
  "does not report credits for unrelated SDK failure %s", (message) => {
    expect(isElevenLabsAccountRestriction(new Error(message), "sdk")).toBe(false);
  },
);

it("uses the requested wording and a stable toast identity", () => {
  vi.mocked(toast.error).mockClear();
  expect(notifyElevenLabsError({ provider_error_code: ELEVENLABS_ACCOUNT_RESTRICTED })).toBe(true);
  expect(toast.error).toHaveBeenCalledWith(ELEVENLABS_CREDITS_MESSAGE, {
    id: "elevenlabs-account-restricted", duration: 10000, closeButton: true,
  });
  expect(ELEVENLABS_CREDITS_MESSAGE).toBe("Our agents were about to respond, but we detected that your ElevenLabs credits are 0. Refill your balance to try again.");
  expect(notifyElevenLabsError(new Error("Network unavailable"))).toBe(false);
  expect(toast.error).toHaveBeenCalledTimes(1);
});

it.each([
  { reason: "user", message: "User ended the conversation" },
  { reason: "agent", message: "Conversation complete" },
  new Error("Microphone permission denied"),
])("does not notify for an ordinary ending or microphone error %j", (failure) => {
  vi.mocked(toast.error).mockClear();
  expect(notifyElevenLabsError(failure, "sdk")).toBe(false);
  expect(toast.error).not.toHaveBeenCalled();
});
