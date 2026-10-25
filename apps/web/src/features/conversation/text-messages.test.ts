import { describe, expect, it } from "vitest";
import { customerMessage, PendingTextEchoes } from "./text-messages";

describe("customer text messages", () => {
  it("bounds message size before anything is sent or recorded", () => {
    expect(customerMessage("  My AC is not cooling.  ")).toBe(
      "My AC is not cooling.",
    );
    expect(() => customerMessage(" \n ")).toThrow();
    expect(() => customerMessage("x".repeat(2_001))).toThrow();
  });

  it("suppresses only the pending provider echo, even after another response", () => {
    const echoes = new PendingTextEchoes();
    echoes.add("Yes, confirm my appointment.", 1_000);
    expect(echoes.consume("I can help with that.", 1_001)).toBe(false);
    expect(echoes.consume("Yes, confirm my appointment.", 1_002)).toBe(true);
    expect(echoes.consume("Yes, confirm my appointment.", 1_003)).toBe(false);
  });

  it("does not discard later speech or messages after expiry or a new session", () => {
    const echoes = new PendingTextEchoes();
    echoes.add("Yes", 1_000);
    expect(echoes.consume("Yes", 31_001)).toBe(false);
    echoes.add("A different address", 32_000);
    echoes.clear();
    expect(echoes.consume("A different address", 32_001)).toBe(false);
  });
});
