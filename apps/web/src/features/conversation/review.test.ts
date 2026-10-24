import { describe, expect, it } from "vitest";

import { appendTranscript, validateConfirmation } from "./review";

describe("conversation review", () => {
  it("replaces an adjacent partial transcript instead of duplicating it", () => {
    expect(
      appendTranscript(
        [{ speaker: "USER", text: "I need AC" }],
        "USER",
        "I need AC repair",
      ),
    ).toEqual([{ speaker: "USER", text: "I need AC repair" }]);
  });

  it("requires contact, intent, and both conversation speakers", () => {
    expect(
      validateConfirmation(
        {
          fullName: "Synthetic Customer",
          email: "",
          phone: "",
          intakeIntent: "AC repair",
        },
        [
          { speaker: "AGENT", text: "How may I help?" },
          { speaker: "USER", text: "I need AC repair." },
        ],
      ),
    ).toBe("Email or phone is required.");

    expect(
      validateConfirmation(
        {
          fullName: "Synthetic Customer",
          email: "synthetic@example.test",
          phone: "",
          intakeIntent: "AC repair",
        },
        [
          { speaker: "AGENT", text: "How may I help?" },
          { speaker: "USER", text: "I need AC repair." },
        ],
      ),
    ).toBeUndefined();
  });
});
