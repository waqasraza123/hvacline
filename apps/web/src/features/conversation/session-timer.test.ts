import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { SessionTimer, remainingSessionSeconds } from "./session-timer";

it("counts down against a deadline even when the tab skips timer ticks", () => {
  const started = Date.parse("2026-11-02T12:00:00Z");
  const deadline = started + 180000;
  expect(remainingSessionSeconds(deadline, started)).toBe(180);
  expect(remainingSessionSeconds(deadline, started + 1001)).toBe(179);
  expect(remainingSessionSeconds(deadline, started + 179001)).toBe(1);
  expect(remainingSessionSeconds(deadline, started + 240000)).toBe(0);
});

it("shows three minutes initially and zero at expiry without live announcements every second", () => {
  const render = (remaining: number) =>
    renderToStaticMarkup(
      createElement(SessionTimer, { remaining, maximum: 180, active: true }),
    );
  expect(render(180)).toContain("3:00");
  expect(render(0)).toContain("0:00");
  expect(render(0)).toContain('role="timer"');
  expect(render(0)).toContain('aria-live="off"');
  expect(render(0)).toContain('data-urgent="true"');
});
