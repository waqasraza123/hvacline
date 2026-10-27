import { afterEach, expect, it, vi } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { OperationsApiError } from "../operations/api";
import { BookingProgressPanel } from "./booking-progress-panel";
import { BrowserBooking } from "./browser-booking";
import {
  INITIAL_BOOKING_PROGRESS,
  bookingFailure,
  bookingPresentation,
  conversationActivity,
} from "./booking-progress";
import type { BookingProgress } from "./booking-progress";
import type { VoiceAppointment } from "./voice-booking";

afterEach(() => vi.useRealTimers());

const now = Date.parse("2026-11-02T12:00:00Z");
const appointment: VoiceAppointment = {
  appointment: {
    id: "appointment-1",
    service_request_id: "request-1",
    team_key: "test-team",
    starts_at: "2026-11-03T15:00:00Z",
    ends_at: "2026-11-03T16:00:00Z",
    hold_expires_at: "2026-11-02T12:05:00Z",
    status: "HELD",
  },
  timezone: "America/New_York",
  readback: "Please confirm the selected appointment.",
};
const saved: BookingProgress = {
  ...INITIAL_BOOKING_PROGRESS,
  requestSaved: true,
  serviceKind: "AC_REPAIR",
};

it("distinguishes draft details, intake readback, saved request, hold, and confirmed booking", () => {
  expect(
    bookingPresentation(INITIAL_BOOKING_PROGRESS, undefined, now).stage,
  ).toBe(0);
  expect(
    bookingPresentation(
      { ...INITIAL_BOOKING_PROGRESS, awaitingIntakeConfirmation: true },
      undefined,
      now,
    ).stage,
  ).toBe(1);
  expect(bookingPresentation(saved, undefined, now)).toMatchObject({
    stage: 2,
    confirmed: false,
  });
  expect(bookingPresentation(saved, appointment, now)).toMatchObject({
    stage: 2,
    confirmed: false,
    remaining: 300,
  });
  expect(
    bookingPresentation(
      saved,
      {
        ...appointment,
        appointment: { ...appointment.appointment, status: "CONFIRMED" },
      },
      now,
    ),
  ).toMatchObject({ stage: 3, confirmed: true, remaining: 0 });
});

it("expires a hold without expiring a confirmed booking", () => {
  const expired = bookingPresentation(saved, appointment, now + 300_000);
  expect(expired.remaining).toBe(0);
  expect(expired.message).toContain("expired");
  expect(expired.confirmed).toBe(false);
  const confirmed = {
    ...appointment,
    appointment: { ...appointment.appointment, status: "CONFIRMED" },
  };
  expect(bookingPresentation(saved, confirmed, now + 600_000).confirmed).toBe(
    true,
  );
});

it("keeps confirmed receipts while hazards override normal booking guidance", () => {
  const confirmed = {
    ...appointment,
    appointment: { ...appointment.appointment, status: "CONFIRMED" },
  };
  const view = bookingPresentation(
    { ...saved, hazardous: true, pending: "check_appointment_availability" },
    confirmed,
    now,
  );
  expect(view.confirmed).toBe(true);
  expect(view.message).toContain("emergency services");
  expect(view.message).not.toContain("Checking");
});

it("shows distinct unavailable-date, service-area and unconfigured outcomes", () => {
  const availability = {
    configured: true,
    in_service_area: true,
    timezone: "America/New_York",
    slots: [],
    message: null,
  };
  expect(
    bookingPresentation({ ...saved, availability }, undefined, now).message,
  ).toContain("No times");
  expect(
    bookingPresentation(
      { ...saved, availability: { ...availability, in_service_area: false } },
      undefined,
      now,
    ).message,
  ).toContain("outside");
  expect(
    bookingPresentation(
      { ...saved, availability: { ...availability, configured: false } },
      undefined,
      now,
    ).message,
  ).toContain("not configured");
});

it("separates uncertain writes from rejected confirmations and local validation failures", () => {
  const unknown = bookingFailure(
    "confirm_appointment",
    new TypeError("Connection lost"),
  );
  expect(unknown.uncertain).toBe(true);
  expect(
    bookingPresentation({ ...saved, failure: unknown }, appointment, now)
      .message,
  ).toContain("unresolved");
  expect(
    bookingFailure(
      "confirm_service_request",
      new OperationsApiError(422, "Readback rejected"),
    ),
  ).toMatchObject({ uncertain: false });
  expect(
    bookingFailure("reserve_appointment", new Error("Choose a slot"), false)
      .uncertain,
  ).toBe(false);
  expect(
    bookingFailure(
      "check_appointment_availability",
      new TypeError("Connection lost"),
    ).uncertain,
  ).toBe(false);
});

it("never labels a muted or disconnected client as listening", () => {
  const client = {
    status: "connected",
    mode: "listening",
    isMuted: false,
  } as const;
  expect(conversationActivity("active", client, "VOICE")).toContain(
    "listening",
  );
  expect(
    conversationActivity("active", { ...client, isMuted: true }, "VOICE"),
  ).toBe("Microphone muted");
  expect(
    conversationActivity(
      "active",
      { ...client, status: "disconnected" },
      "VOICE",
    ),
  ).toContain("interrupted");
  expect(conversationActivity("saved", client, "VOICE")).toBe(
    "Conversation ended",
  );
  expect(conversationActivity("active", client, "TEXT")).toContain(
    "microphone off",
  );
  expect(
    conversationActivity("active", { ...client, mode: undefined }, "VOICE"),
  ).toBe("Voice connected");
});

it("renders a prominent receipt after disconnect and restricts navigation during a conversation", () => {
  const confirmed = {
    ...appointment,
    appointment: { ...appointment.appointment, status: "CONFIRMED" },
  };
  const render = (conversationBusy: boolean) =>
    renderToStaticMarkup(
      createElement(BookingProgressPanel, {
        progress: saved,
        appointment: confirmed,
        activity: conversationBusy ? "Line is speaking" : "Conversation ended",
        conversationBusy,
        conversationEnded: !conversationBusy,
        onViewAppointments: vi.fn(),
        onViewBooking: vi.fn(),
      }),
    );
  expect(render(true)).toContain("disabled");
  const ended = render(false);
  expect(ended).toContain("Appointment confirmed");
  expect(ended).toContain("America/New_York");
  expect(ended).toContain("AC repair");
  expect(ended).toContain("View my appointments");
  expect(ended).toContain("View booking details");
  expect(ended).not.toContain("disabled");
  expect(ended).toContain('aria-current="step"');
});

it("keeps hold countdown text outside the live status announcement", () => {
  vi.useFakeTimers();
  vi.setSystemTime(now);
  const markup = renderToStaticMarkup(
    createElement(BookingProgressPanel, {
      progress: saved,
      appointment,
      activity: "Line is listening",
      conversationBusy: true,
      conversationEnded: false,
    }),
  );
  expect(markup).toContain('aria-live="off"');
  expect(markup).toContain("Hold remaining:");
  expect(markup).toContain("5:00");
  expect(markup).toContain("confirmation required");
});

it("disables an expired hold but allows an unresolved confirmation to be checked", () => {
  vi.useFakeTimers();
  vi.setSystemTime(now + 600_000);
  const props = {
    apiBaseUrl: "",
    serviceRequestId: "request-1",
    postalCode: "10001",
    hazardous: false,
    initialAppointment: appointment.appointment,
    initialTimezone: appointment.timezone,
  };
  const expired = renderToStaticMarkup(createElement(BrowserBooking, props));
  expect(expired).toMatch(/<button disabled="">I agree/);
  const unresolved = renderToStaticMarkup(
    createElement(BrowserBooking, {
      ...props,
      initialFailure: bookingFailure(
        "confirm_appointment",
        new TypeError("Connection lost"),
      ),
    }),
  );
  expect(unresolved).toContain("Confirmation result unresolved");
  expect(unresolved).toContain("<button>Check previous confirmation</button>");
});

it("does not create a fresh fallback reservation after losing the live session’s reservation response", () => {
  const markup = renderToStaticMarkup(
    createElement(BrowserBooking, {
      apiBaseUrl: "",
      serviceRequestId: "request-1",
      postalCode: "10001",
      hazardous: false,
      initialFailure: bookingFailure(
        "reserve_appointment",
        new TypeError("Connection lost"),
      ),
    }),
  );
  expect(markup).toContain("previous reservation result is unresolved");
  expect(markup).not.toContain("<form");
});
