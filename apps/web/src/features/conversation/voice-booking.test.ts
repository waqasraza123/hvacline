import { afterEach, expect, it, vi } from "vitest";

import { VoiceBookingSession } from "./voice-booking";
import type { BookingProgress } from "./booking-progress";

afterEach(() => vi.unstubAllGlobals());

const draft = {
  fullName: "Fictional Caller",
  phone: "+12025550123",
  addressLine1: "123 Example Street",
  city: "New York",
  stateCode: "NY",
  postalCode: "10001",
  serviceKind: "AC_REPAIR",
  intakeIntent: "AC is not cooling",
  preferredWindow: "Morning",
  hazardousCondition: false,
};

function session() {
  return new VoiceBookingSession({
    apiBaseUrl: "https://api.example.test",
    adminToken: "fictional-admin-token",
    sessionId: "session-1",
    isActive: () => true,
    onSaved: vi.fn(),
    onAppointment: vi.fn(),
  });
}

it("preserves the exact confirmed payload and key after a lost save response", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        readback: "Read back the fictional details.",
        business_date: "2026-10-25",
        timezone: "America/New_York",
      }),
    )
    .mockRejectedValueOnce(new TypeError("Network interrupted"))
    .mockResolvedValueOnce(
      Response.json({
        conversation_intake_id: "intake-1",
        service_request_id: "request-1",
        customer: { id: "customer-1", full_name: draft.fullName },
        confirmed_at: "2026-10-25T12:00:00Z",
      }),
    );
  vi.stubGlobal("fetch", fetcher);
  const booking = session();
  await booking.updateDraft(draft);
  await booking.execute("prepare_intake_confirmation", {});
  booking.recordTurn("AGENT", "Read back the fictional details.");
  booking.recordTurn("USER", "Yes, save my request.");
  await booking.execute("confirm_service_request", {
    explicit_confirmation: true,
  });
  booking.recordTurn("AGENT", "I will retry that save.");
  await booking.execute("confirm_service_request", {
    explicit_confirmation: true,
  });
  const first = fetcher.mock.calls[1][1];
  const retry = fetcher.mock.calls[2][1];
  expect(retry.body).toBe(first.body);
  expect(retry.headers["Idempotency-Key"]).toBe(
    first.headers["Idempotency-Key"],
  );
  expect(retry.headers["X-Demo-Admin-Token"]).toBe("fictional-admin-token");
  expect(booking.savedIntake?.serviceRequestId).toBe("request-1");
});

it("does not query slots or reserve appointments before intake confirmation", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const booking = session();
  await booking.updateDraft(draft);
  expect(
    await booking.execute("check_appointment_availability", {
      day: "2026-10-26",
    }),
  ).toMatchObject({ ok: false });
  expect(
    await booking.execute("reserve_appointment", {
      team_key: "team-a",
      starts_at: "2026-10-26T13:00:00Z",
    }),
  ).toMatchObject({ ok: false });
  expect(fetcher).not.toHaveBeenCalled();
});

const intakeResponse = {
  conversation_intake_id: "intake-1",
  service_request_id: "request-1",
  customer: { id: "customer-1", full_name: draft.fullName },
  confirmed_at: "2026-10-25T12:00:00Z",
};
const heldResponse = {
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
  readback: "Confirm the selected time.",
};
const availabilityResponse = {
  configured: true,
  in_service_area: true,
  timezone: "America/New_York",
  message: null,
  slots: [
    {
      team_key: "test-team",
      starts_at: heldResponse.appointment.starts_at,
      ends_at: heldResponse.appointment.ends_at,
    },
  ],
};

function progressSession() {
  const onProgress = vi.fn<(value: BookingProgress) => void>();
  const onAppointment = vi.fn();
  const booking = new VoiceBookingSession({
    apiBaseUrl: "https://api.example.test",
    sessionId: "session-1",
    isActive: () => true,
    onSaved: vi.fn(),
    onAppointment,
    onProgress,
  });
  return {
    booking,
    onProgress,
    onAppointment,
    latest: () => onProgress.mock.calls.at(-1)?.[0],
  };
}

async function saveRequest(booking: VoiceBookingSession) {
  await booking.updateDraft(draft);
  await booking.execute("prepare_intake_confirmation", {});
  booking.recordTurn("AGENT", "Read back the fictional details.");
  booking.recordTurn("USER", "Yes");
  await booking.execute("confirm_service_request", {
    explicit_confirmation: true,
  });
}

it("publishes pending work immediately and advances only when a request resolves", async () => {
  let resolveReadback!: (value: Response) => void;
  const fetcher = vi.fn().mockImplementationOnce(
    () =>
      new Promise<Response>((resolve) => {
        resolveReadback = resolve;
      }),
  );
  vi.stubGlobal("fetch", fetcher);
  const { booking, latest, onProgress } = progressSession();
  await booking.updateDraft(draft);
  const preparing = booking.execute("prepare_intake_confirmation", {});
  expect(latest()).toMatchObject({
    pending: "prepare_intake_confirmation",
    awaitingIntakeConfirmation: false,
    requestSaved: false,
  });
  const count = onProgress.mock.calls.length;
  expect(
    await booking.execute("confirm_service_request", {
      explicit_confirmation: true,
    }),
  ).toMatchObject({ ok: false });
  expect(onProgress).toHaveBeenCalledTimes(count);
  resolveReadback(
    Response.json({ readback: "Read back the fictional details." }),
  );
  await preparing;
  expect(latest()).toMatchObject({
    pending: undefined,
    awaitingIntakeConfirmation: true,
    requestSaved: false,
  });
  await booking.updateDraft({ addressLine1: "125 Example Street" });
  expect(latest()).toMatchObject({
    awaitingIntakeConfirmation: false,
    requestSaved: false,
  });
});

it("publishes saved, availability, held and confirmed results without repeating booking writes", async () => {
  const confirmed = {
    ...heldResponse,
    appointment: { ...heldResponse.appointment, status: "CONFIRMED" },
  };
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({ readback: "Read back the fictional details." }),
    )
    .mockResolvedValueOnce(Response.json(intakeResponse))
    .mockResolvedValueOnce(Response.json(availabilityResponse))
    .mockResolvedValueOnce(Response.json(heldResponse))
    .mockResolvedValueOnce(Response.json(confirmed));
  vi.stubGlobal("fetch", fetcher);
  const { booking, latest, onAppointment } = progressSession();
  await saveRequest(booking);
  expect(latest()).toMatchObject({
    requestSaved: true,
    pending: undefined,
    serviceKind: "AC_REPAIR",
  });
  await booking.execute("check_appointment_availability", {
    day: "2026-11-03",
  });
  expect(latest()?.availability?.slots).toEqual(availabilityResponse.slots);
  await booking.execute("reserve_appointment", availabilityResponse.slots[0]);
  expect(onAppointment).toHaveBeenLastCalledWith(heldResponse);
  booking.recordTurn("AGENT", heldResponse.readback);
  booking.recordTurn("USER", "Yes");
  await booking.execute("confirm_appointment", { explicit_confirmation: true });
  expect(onAppointment).toHaveBeenLastCalledWith(confirmed);
  await booking.execute("confirm_appointment", { explicit_confirmation: true });
  expect(fetcher).toHaveBeenCalledTimes(5);
  expect(latest()?.failure).toBeUndefined();
});

it("retains an unresolved reservation and its retry key until the same action succeeds", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({ readback: "Read back the fictional details." }),
    )
    .mockResolvedValueOnce(Response.json(intakeResponse))
    .mockResolvedValueOnce(Response.json(availabilityResponse))
    .mockRejectedValueOnce(new TypeError("Connection lost"))
    .mockResolvedValueOnce(Response.json(heldResponse));
  vi.stubGlobal("fetch", fetcher);
  const { booking, latest, onAppointment } = progressSession();
  await saveRequest(booking);
  await booking.execute("check_appointment_availability", {
    day: "2026-11-03",
  });
  await booking.execute("reserve_appointment", availabilityResponse.slots[0]);
  expect(latest()).toMatchObject({
    requestSaved: true,
    failure: { operation: "reserve_appointment", uncertain: true },
  });
  expect(onAppointment).not.toHaveBeenCalled();
  await booking.execute("reserve_appointment", {
    team_key: "other-team",
    starts_at: "2026-11-03T17:00:00Z",
  });
  expect(latest()?.failure?.uncertain).toBe(true);
  expect(fetcher).toHaveBeenCalledTimes(4);
  await booking.execute("reserve_appointment", availabilityResponse.slots[0]);
  expect(fetcher.mock.calls[3][1].body).toBe(fetcher.mock.calls[4][1].body);
  expect(onAppointment).toHaveBeenLastCalledWith(heldResponse);
  expect(latest()?.failure).toBeUndefined();
});

it("keeps a saved request when a hold is released and hazards remain sticky", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({ readback: "Read back the fictional details." }),
    )
    .mockResolvedValueOnce(Response.json(intakeResponse))
    .mockResolvedValueOnce(Response.json(availabilityResponse))
    .mockResolvedValueOnce(Response.json(heldResponse))
    .mockResolvedValueOnce(Response.json({ released: true }))
    .mockResolvedValueOnce(Response.json({ human_attention_required: true }))
    .mockResolvedValueOnce(Response.json({ human_attention_required: true }));
  vi.stubGlobal("fetch", fetcher);
  const { booking, latest, onAppointment } = progressSession();
  await saveRequest(booking);
  await booking.execute("check_appointment_availability", {
    day: "2026-11-03",
  });
  await booking.execute("reserve_appointment", availabilityResponse.slots[0]);
  await booking.execute("release_appointment_hold", {});
  expect(onAppointment).toHaveBeenLastCalledWith(undefined);
  expect(latest()).toMatchObject({
    requestSaved: true,
    availability: undefined,
  });
  await booking.updateDraft({ hazardousCondition: true });
  await booking.updateDraft({ hazardousCondition: false });
  expect(latest()?.hazardous).toBe(true);
  expect(
    await booking.execute("check_appointment_availability", {
      day: "2026-11-03",
    }),
  ).toMatchObject({ ok: false });
});

it("returns the exact readback after a rejected confirmation and uses the fresh reply", async () => {
  const readback =
    "Please confirm all fictional details exactly. Reply yes to save my request.";
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(Response.json({ readback }))
    .mockResolvedValueOnce(
      Response.json(
        { error: { message: "Full readback required" } },
        { status: 422 },
      ),
    )
    .mockResolvedValueOnce(
      Response.json({
        conversation_intake_id: "intake-1",
        service_request_id: "request-1",
        customer: { id: "customer-1", full_name: draft.fullName },
        confirmed_at: "2026-10-25T12:00:00Z",
      }),
    );
  vi.stubGlobal("fetch", fetcher);
  const booking = session();
  await booking.updateDraft(draft);
  await booking.execute("prepare_intake_confirmation", {});
  booking.recordTurn("AGENT", "Shortened details. Is this correct?");
  booking.recordTurn("USER", "Yes");
  expect(
    await booking.execute("confirm_service_request", {
      explicit_confirmation: true,
    }),
  ).toMatchObject({
    ok: false,
    request_saved: false,
    code: "INTAKE_CONFIRMATION_REQUIRED",
    readback,
  });
  booking.recordTurn("AGENT", readback);
  booking.recordTurn("USER", "Confirm");
  expect(
    await booking.execute("confirm_service_request", {
      explicit_confirmation: true,
    }),
  ).toMatchObject({ ok: true, persisted: true });
  const retry = JSON.parse(fetcher.mock.calls[2][1].body);
  expect(retry.transcript.slice(-2)).toEqual([
    { speaker: "AGENT", text: readback },
    { speaker: "USER", text: "Confirm" },
  ]);
});

it("requires collecting the hazard flag and invalidates prepared details on corrections", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(Response.json({ readback: "Fictional readback" }));
  vi.stubGlobal("fetch", fetcher);
  const booking = session();
  await booking.updateDraft({ ...draft, hazardousCondition: undefined });
  expect(
    await booking.execute("prepare_intake_confirmation", {}),
  ).toMatchObject({ ok: false });
  expect(fetcher).not.toHaveBeenCalled();
  await booking.updateDraft({ hazardousCondition: false });
  expect(
    await booking.execute("prepare_intake_confirmation", {}),
  ).toMatchObject({ ok: true });
  await booking.updateDraft({ addressLine1: "125 Example Street" });
  expect(
    await booking.execute("confirm_service_request", {
      explicit_confirmation: true,
    }),
  ).toMatchObject({ ok: false });
  expect(fetcher).toHaveBeenCalledTimes(1);
});
