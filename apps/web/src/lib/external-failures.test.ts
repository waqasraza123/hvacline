import { expect, it, vi, afterEach, beforeEach } from "vitest";
import { toast } from "sonner";
import { EXTERNAL_FAILURES_HEADER, externalFailureHeaders, externalFailureMessage, parseExternalFailures } from "./external-failures";
import { notifyExternalFailures } from "./external-failure-toast";
import { providerFetch } from "./provider-fetch";

vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));
beforeEach(() => vi.stubGlobal("window", {}));
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

it("accepts only known provider/kind metadata and strips private fields", () => {
  const value = [{ provider: "stripe", kind: "access", message: "must-not-leak" }, { provider: "attacker", kind: "billing" }, { provider: "twilio", kind: "made-up" }];
  expect(parseExternalFailures(value)).toEqual([{ provider: "stripe", kind: "access" }]);
  const headers = externalFailureHeaders(new Response(null, { headers: { [EXTERNAL_FAILURES_HEADER]: JSON.stringify(value) } }));
  expect(headers).toEqual({ [EXTERNAL_FAILURES_HEADER]: '[{"provider":"stripe","kind":"access"}]' });
  expect(parseExternalFailures("__proto__")).toEqual([]);
});

it("recognizes saved job failures without reading free text", () => {
  expect(parseExternalFailures({ items: [{ attempts: [{ failure_code: "EXTERNAL_TWILIO_BILLING" }] }], recent: [{ last_error: "EXTERNAL_RESEND_RATE_LIMITED" }] })).toEqual([
    { provider: "resend", kind: "rate_limited" }, { provider: "twilio", kind: "billing" },
  ]);
  expect(parseExternalFailures({ error: { code: "AUTHENTICATION_REQUIRED", status: 403, message: "Stripe access denied" } })).toEqual([]);
});

it("does not invent a zero credit balance for provider errors", () => {
  expect(externalFailureMessage({ provider: "openai", kind: "billing" })).toContain("billing limit");
  expect(externalFailureMessage({ provider: "openai", kind: "billing" })).not.toContain("0");
  expect(externalFailureMessage({ provider: "google_calendar", kind: "rate_limited" })).toContain("Google Calendar");
});

it("notifies on safe external metadata while leaving response and body readable", async () => {
  const response = Response.json({ error: { code: "EXTERNAL_FAILED", details: { external_failures: [{ provider: "telnyx", kind: "access" }] } } }, {
    status: 424, headers: { [EXTERNAL_FAILURES_HEADER]: '[{"provider":"telnyx","kind":"access"}]' },
  });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  const result = await providerFetch("/api/outbound-demo");
  expect(result).toBe(response);
  expect(result.status).toBe(424);
  expect((await result.json()).error.code).toBe("EXTERNAL_FAILED");
  expect(toast.error).toHaveBeenCalledTimes(1);
  expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("Telnyx denied access"), expect.objectContaining({ id: "external-telnyx-access" }));
});

it("keeps application errors and browser network failures out of provider notifications", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ error: { message: "Internal error", code: "SERVER_ERROR" } }, { status: 500 })));
  await providerFetch("/api/workspace/list");
  vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Network unavailable"));
  await expect(providerFetch("/api/workspace/list")).rejects.toThrow("Network unavailable");
  expect(toast.error).not.toHaveBeenCalled();
});

it("preserves the approved ElevenLabs copy without a second generic toast", () => {
  notifyExternalFailures({ external_failures: [{ provider: "elevenlabs", kind: "billing" }], error: { details: { provider_error_code: "ELEVENLABS_ACCOUNT_RESTRICTED" } } });
  expect(toast.error).toHaveBeenCalledTimes(1);
  expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("ElevenLabs credits are 0"), expect.objectContaining({ id: "elevenlabs-account-restricted" }));
});

it("prefers precise metadata over the legacy generic code for the same provider", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({
    error: { code: "STRIPE_UNAVAILABLE", details: {
      external_failures: [{ provider: "stripe", kind: "access" }],
    } },
  }, { status: 424 })));
  await providerFetch("/api/billing/checkout");
  expect(toast.error).toHaveBeenCalledTimes(1);
  expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("Stripe denied access"), expect.anything());
});

it("leaves server requests readable without calling client notifications", async () => {
  vi.stubGlobal("window", undefined);
  const response = Response.json({ error: { code: "STRIPE_UNAVAILABLE" } }, { status: 502 });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  const result = await providerFetch("https://api.example/settings");
  expect(await result.json()).toEqual({ error: { code: "STRIPE_UNAVAILABLE" } });
  expect(toast.error).not.toHaveBeenCalled();
});

it("bounds body inspection without trusting a missing content-length", async () => {
  const large = JSON.stringify({ padding: "x".repeat(1_048_576), error: { code: "STRIPE_UNAVAILABLE" } });
  const response = new Response(large, { headers: { "Content-Type": "application/json" } });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  const result = await providerFetch("/api/workspace/list");
  expect(await result.text()).toBe(large);
  expect(toast.error).not.toHaveBeenCalled();
});

it("still uses safe headers when the body is unreadable", async () => {
  const response = new Response("not-json", { status: 424, headers: {
    "Content-Type": "application/json",
    [EXTERNAL_FAILURES_HEADER]: '[{"provider":"resend","kind":"timeout"}]',
  } });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  expect(await (await providerFetch("/api/example")).text()).toBe("not-json");
  expect(toast.error).toHaveBeenCalledTimes(1);
});
