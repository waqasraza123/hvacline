import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { BookingLimitSummary } from "./booking-limits";

it("shows configured backend limits and remaining booking places", () => {
  const markup = renderToStaticMarkup(
    createElement(BookingLimitSummary, {
      limits: {
        max_active_appointments: 2,
        max_booking_changes: 4,
        active_appointments: 1,
        appointments_remaining: 1,
        refresh_at: null,
      },
    }),
  );
  expect(markup).toContain("2 active appointments");
  expect(markup).toContain("4 date/time changes");
  expect(markup).toContain("1 of 2 appointment places used");
  expect(markup).toContain("1 available");
});

it("explains that an active booking or hold consumes the only place", () => {
  const markup = renderToStaticMarkup(
    createElement(BookingLimitSummary, {
      limits: {
        max_active_appointments: 1,
        max_booking_changes: 1,
        active_appointments: 1,
        appointments_remaining: 0,
        refresh_at: null,
      },
    }),
  );
  expect(markup).toContain("1 date/time change");
  expect(markup).toContain("appointment limit is reached");
  expect(markup).toContain("Unexpired holds use a place");
});
