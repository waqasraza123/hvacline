import { describe, expect, it } from "vitest";
import { parseMemory } from "./memory";

const view = {
  available: true, enabled: true, revision: 2, retention_days: 90,
  whatsapp_linked: false,
  options: { appointment_time: { MORNING: "morning appointments" } },
  facts: [{ key: "appointment_time", value: "MORNING", source_kind: "CUSTOMER_CONTROL",
    updated_at: "2026-10-28T00:00:00Z", expires_at: "2027-01-26T00:00:00Z" }],
  sources: [{ intake_id: "synthetic-source", summary: "Authorized conversation.",
    suggestions: [{ key: "appointment_time", value: "MORNING" }] }],
};

describe("customer memory controls", () => {
  it("retains the revision and provenance needed to review a correction", () => {
    const parsed = parseMemory(view);
    expect(parsed.revision).toBe(2);
    expect(parsed.facts[0].source_kind).toBe("CUSTOMER_CONTROL");
    expect(parsed.sources[0].suggestions[0].value).toBe("MORNING");
  });

  it.each([
    { ...view, revision: "2" },
    { ...view, facts: [{ key: "appointment_time" }] },
    { ...view, sources: [{ intake_id: "foreign", summary: "bad", suggestions: [null] }] },
  ])("rejects malformed control responses", (value) => {
    expect(() => parseMemory(value)).toThrow();
  });
});
