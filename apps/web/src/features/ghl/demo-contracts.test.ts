import { describe, expect, it } from "vitest";
import { parseGhlDemo } from "./demo-contracts";

function snapshot() {
  return {
    state: "live",
    token: "must-not-reach-the-view",
    snapshot: {
      sampled_at: "2026-11-16T10:00:00Z",
      sample_limit: 100,
      has_more: false,
      location_id: "must-not-reach-the-view",
      counts: { loaded: 1, open: 1, won: 0, lost: 0, abandoned: 0 },
      pipelines: [
        {
          name: "Fictional HVAC",
          contact: { email: "private@example.invalid" },
          stages: [{ name: "New request", count: 1, id: "private-stage" }],
        },
      ],
    },
  };
}

describe("public GoHighLevel demo boundary", () => {
  it("keeps only the public aggregate projection", () => {
    const result = parseGhlDemo(snapshot());
    expect(result.state).toBe("live");
    expect(result.snapshot?.counts.loaded).toBe(1);
    const text = JSON.stringify(result);
    expect(text).not.toContain("must-not-reach-the-view");
    expect(text).not.toContain("private@example.invalid");
    expect(text).not.toContain("private-stage");
  });

  it("keeps a previous snapshot visibly unavailable after a refresh failure", () => {
    const value = snapshot();
    value.state = "unavailable";
    const result = parseGhlDemo(value);
    expect(result.state).toBe("unavailable");
    expect(result.snapshot?.sampled_at).toBe(value.snapshot.sampled_at);
  });

  it.each(["disabled", "unavailable"])("allows an empty %s state", (state) => {
    expect(parseGhlDemo({ state, snapshot: null })).toEqual({
      state,
      snapshot: null,
    });
  });

  it("rejects inconsistent totals instead of showing misleading metrics", () => {
    const value = snapshot();
    value.snapshot.counts.loaded = 2;
    expect(() => parseGhlDemo(value)).toThrow();
    const stages = snapshot();
    stages.snapshot.pipelines[0].stages[0].count = 0;
    expect(() => parseGhlDemo(stages)).toThrow();
  });

  it("rejects live-without-data and coerced status values", () => {
    expect(() => parseGhlDemo({ state: "live", snapshot: null })).toThrow();
    expect(() => parseGhlDemo({ ...snapshot(), state: ["live"] })).toThrow();
  });
});
