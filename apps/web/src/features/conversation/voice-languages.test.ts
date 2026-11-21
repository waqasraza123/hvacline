import { expect, it } from "vitest";
import { ProviderLanguageObserver, parseVoiceLanguageSession } from "@insurance-operations/customer-core";

const grant = { language: "en", allowed_languages: ["en", "es"], automatic_switching: true, overrides: { agent: { language: "en" } } };
const event = { tool_name: "language_detection", tool_type: "system", tool_call_id: "fictional-tool-1", is_called: true, is_error: false };
it("does not claim success from a tool request, incomplete result or failure", () => {
  const observer = new ProviderLanguageObserver();
  observer.start(parseVoiceLanguageSession(grant));
  expect(observer.receive({ tool_name: "language_detection" })).toBeUndefined();
  expect(observer.receive(event)).toEqual({ kind: "unobserved" });
  expect(observer.receive({ ...event, is_error: true })).toEqual({ kind: "failed" });
});
it("updates only from successful full provider results for authorized languages and deduplicates", () => {
  const observer = new ProviderLanguageObserver();
  observer.start(parseVoiceLanguageSession(grant));
  const result = { ...event, full_tool_result: JSON.stringify({ language: "es", status: "success" }) };
  expect(observer.receive(result)).toEqual({ kind: "switched", language: "es" });
  expect(observer.receive(result)).toBeUndefined();
  expect(observer.receive({ ...result, tool_call_id: "fictional-tool-2", full_tool_result: JSON.stringify({ language: "ur" }) })).toEqual({ kind: "failed" });
  observer.start();
  expect(observer.receive(result)).toBeUndefined();
});
it("rejects forged overrides and languages outside the authorized list", () => {
  expect(() => parseVoiceLanguageSession({ ...grant, language: "ur" })).toThrow();
  expect(() => parseVoiceLanguageSession({ ...grant, overrides: { agent: { language: "es" } } })).toThrow();
});
