import { afterEach, expect, it, vi } from "vitest";

import { VoiceBookingSession } from "./voice-booking";

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
