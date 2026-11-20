import { describe, expect, it } from "vitest";
import { availableDemoSlots, demoMetrics, demoReducer, initialDemo } from "./demo";

describe("isolated lead recovery simulation", () => {
  it("loads the deterministic fictional cohort and honest estimates", () => {
    const state = initialDemo();
    expect(demoMetrics(state)).toEqual({ total: 24, recovered: 8, scheduled: 6, awaiting: 5, conversion: 8 / 24, revenue: 5200 });
    expect(state.cases.filter((row) => ["NEEDS_REVIEW", "CLOSED"].includes(row.status))).toHaveLength(5);
    expect(initialDemo()).toEqual(state);
  });
  it("requires a customer response and explicit slot confirmation", () => {
    const initial = initialDemo();
    expect(demoReducer(initial, { type: "BOOK", slotId: "demo-slot-1" })).toBe(initial);
    let state = demoReducer(initial, { type: "START" });
    expect(demoMetrics(state).recovered).toBe(8);
    expect(demoReducer(state, { type: "BOOK", slotId: "demo-slot-1" })).toBe(state);
    state = demoReducer(state, { type: "YES" });
    state = demoReducer(state, { type: "BOOK", slotId: "demo-slot-1" });
    expect(demoMetrics(state).recovered).toBe(9);
    expect(demoMetrics(state).conversion).toBe(0.375);
    expect(state.activity[0].message).toContain("no real appointment");
    expect(demoReducer(state, { type: "BOOK", slotId: "demo-slot-2" })).toBe(state);
    expect(availableDemoSlots(state).some((slot) => slot.id === "demo-slot-1")).toBe(false);
  });
  it("blocks closed and review cases, and treats STOP as closure", () => {
    let state = initialDemo();
    state = demoReducer(state, { type: "SELECT", id: "demo-recovery-20" });
    expect(demoReducer(state, { type: "START" })).toBe(state);
    state = demoReducer(state, { type: "SELECT", id: "demo-recovery-9" });
    state = demoReducer(state, { type: "START" });
    state = demoReducer(state, { type: "STOP" });
    expect(state.cases.find((row) => row.id === state.selectedId)?.status).toBe("CLOSED");
    expect(demoReducer(state, { type: "START" })).toBe(state);
    expect(demoMetrics(state).recovered).toBe(8);
  });
  it("updates only fictional revenue and resets every demo change", () => {
    let state = demoReducer(initialDemo(), { type: "VALUE", value: 1000 });
    expect(demoMetrics(state).revenue).toBe(8000);
    expect(demoReducer(state, { type: "VALUE", value: -1 })).toBe(state);
    state = demoReducer(state, { type: "START" });
    expect(demoReducer(state, { type: "RESET" })).toEqual(initialDemo());
  });
});
