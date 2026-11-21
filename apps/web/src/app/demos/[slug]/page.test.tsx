import { describe, expect, it, vi } from "vitest";
import DisabledDemoWebsitePage from "./page";

vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("DEMO_NOT_FOUND");
  },
}));

describe("disabled demo App Router entry", () => {
  it("returns not-found instead of rendering the showcase", () => {
    expect(() => DisabledDemoWebsitePage()).toThrow("DEMO_NOT_FOUND");
  });
});
