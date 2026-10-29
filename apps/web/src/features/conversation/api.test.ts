import { afterEach, expect, it, vi } from "vitest";
import {
  authorizeConversationSession,
  ConversationApiError,
  endConversationSession,
} from "./api";
import { lookupConversationApprovedFaq } from "../approved-faqs/api";

afterEach(() => vi.unstubAllGlobals());

it("passes the server session expiry to the countdown", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(
      Response.json({
        session_id: "session-1",
        input_mode: "TEXT",
        connection: {
          transport: "websocket",
          credential: "synthetic-signed-grant",
        },
        maximum_duration_seconds: 180,
        authorization_expires_at: "2030-01-01T12:03:00Z",
        confirmation_expires_at: "2030-01-01T12:30:00Z",
      }),
    ),
  );
  await expect(
    authorizeConversationSession("", undefined, "TEXT"),
  ).resolves.toMatchObject({
    maximumDurationSeconds: 180,
    authorizationExpiresAt: "2030-01-01T12:03:00Z",
  });
});

it("preserves owned-session recovery details without creating another session", async () => {
  const previousSessionId = "00000000-0000-4000-8000-000000000099";
  const fetcher = vi.fn().mockResolvedValueOnce(
    Response.json(
      {
        error: {
          code: "CONVERSATION_ALREADY_ACTIVE",
          message: "Another conversation is already active",
          details: {
            previous_session_id: previousSessionId,
            retry_after_seconds: 120,
          },
        },
      },
      { status: 409 },
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  await expect(
    authorizeConversationSession("", undefined, "TEXT"),
  ).rejects.toMatchObject({
    status: 409,
    previousSessionId,
    retryAfterSeconds: 120,
  });
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("releases a grant rejected because its transport does not match Chat", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        session_id: "00000000-0000-4000-8000-000000000099",
        input_mode: "TEXT",
        connection: { transport: "webrtc", credential: "test-token" },
        maximum_duration_seconds: 180,
        confirmation_expires_at: "2026-10-25T00:00:00Z",
      }),
    )
    .mockResolvedValueOnce(Response.json({ review_available: false }));
  vi.stubGlobal("fetch", fetcher);
  await expect(
    authorizeConversationSession("", undefined, "TEXT"),
  ).rejects.toBeInstanceOf(ConversationApiError);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls[1][0]).toContain(
    "/00000000-0000-4000-8000-000000000099/end",
  );
  expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({
    outcome: "FAILED",
  });
});

it("preserves hosted authorization for browser session, FAQ and end requests", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        session_id: "session-1",
        connection: { transport: "webrtc", credential: "short-lived-token" },
        maximum_duration_seconds: 180,
        confirmation_expires_at: "2026-10-25T00:00:00Z",
      }),
    )
    .mockResolvedValueOnce(
      Response.json({
        matched: false,
        answer: null,
        source: null,
        fallback_message: "Ask the business to follow up.",
      }),
    )
    .mockResolvedValueOnce(Response.json({ review_available: true }));
  vi.stubGlobal("fetch", fetcher);
  const token = "fictional-admin-token";
  await authorizeConversationSession("https://api.example.com", token);
  await lookupConversationApprovedFaq(
    "https://api.example.com",
    "session-1",
    "Hours?",
    token,
  );
  await endConversationSession(
    "https://api.example.com",
    "session-1",
    "COMPLETED",
    token,
  );
  expect(fetcher).toHaveBeenCalledTimes(3);
  for (const [url, options] of fetcher.mock.calls) {
    expect(url).not.toContain(token);
    expect(options.headers["X-Demo-Admin-Token"]).toBe(token);
  }
});

it("authorizes text chat without asserting microphone consent", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(
    Response.json({
      session_id: "text-session",
      input_mode: "TEXT",
      connection: {
        transport: "websocket",
        credential:
          "wss://api.elevenlabs.io/v1/convai/conversation?conversation_signature=fictional",
      },
      maximum_duration_seconds: 180,
      confirmation_expires_at: "2026-10-25T00:00:00Z",
    }),
  );
  vi.stubGlobal("fetch", fetcher);

  const result = await authorizeConversationSession("", undefined, "TEXT");

  expect(result.inputMode).toBe("TEXT");
  expect(result.transport).toBe("websocket");
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    input_mode: "TEXT",
    ai_disclosure_accepted: true,
    microphone_consent_granted: false,
  });
});

it("refuses a voice authorization returned for a text-only request", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(
      Response.json({
        session_id: "incorrect-mode",
        input_mode: "VOICE",
        connection: { transport: "webrtc", credential: "short-lived-token" },
        maximum_duration_seconds: 180,
        confirmation_expires_at: "2026-10-25T00:00:00Z",
      }),
    ),
  );

  await expect(
    authorizeConversationSession("", undefined, "TEXT"),
  ).rejects.toBeInstanceOf(ConversationApiError);
});

it.each([
  ["TEXT", "webrtc"],
  ["VOICE", "websocket"],
  ["TEXT", undefined],
] as const)(
  "refuses %s with an incompatible %s connection",
  async (inputMode, transport) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        Response.json({
          session_id: "wrong-transport",
          input_mode: inputMode,
          connection: { transport, credential: "short-lived-credential" },
          maximum_duration_seconds: 180,
          confirmation_expires_at: "2026-10-25T00:00:00Z",
        }),
      ),
    );
    await expect(
      authorizeConversationSession("", undefined, inputMode),
    ).rejects.toBeInstanceOf(ConversationApiError);
  },
);
