import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { RecoveryDemo } from "./demo-panel";
import { demoReducer, demoSlots, initialDemo } from "./demo";

it("limits the selected-lead timeline to that fictional case", () => {
  const state = initialDemo();
  const html = renderToStaticMarkup(createElement(RecoveryDemo, { state, dispatch: () => {} }));
  const timeline = html.match(/<section\b[^>]*aria-label="Selected lead timeline"[\s\S]*?<\/section>/)?.[0] ?? "";
  expect(timeline).toContain("Fictional missed call scheduled for a simulated follow-up.");
  expect(timeline).not.toContain("Simulated AI follow-up is awaiting a fictional customer response.");
  expect(html).toContain('role="region" aria-label="Fictional recovery leads" tabindex="0"');
  expect(html).toContain('aria-pressed="true"');
  expect(html).toContain('scope="col"');
});

it("announces a simulated confirmation and retains its fictional disclosure", () => {
  let state = initialDemo();
  state = demoReducer(state, { type: "START" });
  state = demoReducer(state, { type: "YES" });
  state = demoReducer(state, { type: "BOOK", slotId: demoSlots[0].id });
  const html = renderToStaticMarkup(createElement(RecoveryDemo, { state, dispatch: () => {} }));
  expect(html).toMatch(/role="status"><small>DEMO DATA · SIMULATED BOOKING CONFIRMATION/);
  expect(html).toContain("No real appointment, calendar event or provider action occurred.");
  expect(html).toContain(demoSlots[0].label);
});
