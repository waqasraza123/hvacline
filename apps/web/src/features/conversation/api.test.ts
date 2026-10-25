import { afterEach, expect, it, vi } from "vitest";
import {
  authorizeConversationSession,
  ConversationApiError,
  endConversationSession,
} from "./api";
import { lookupConversationApprovedFaq } from "../approved-faqs/api";

afterEach(() => vi.unstubAllGlobals());

it("preserves hosted authorization for browser session, FAQ and end requests", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        session_id: "session-1",
        connection: { credential: "short-lived-token" },
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
      connection: { credential: "short-lived-text-token" },
      maximum_duration_seconds: 180,
      confirmation_expires_at: "2026-10-25T00:00:00Z",
    }),
  );
  vi.stubGlobal("fetch", fetcher);

  const result = await authorizeConversationSession("", undefined, "TEXT");

  expect(result.inputMode).toBe("TEXT");
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    input_mode: "TEXT",
    ai_disclosure_accepted: true,
    microphone_consent_granted: false,
    synthetic_data_acknowledged: true,
  });
});

it("refuses a voice authorization returned for a text-only request", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(
      Response.json({
        session_id: "incorrect-mode",
        input_mode: "VOICE",
        connection: { credential: "short-lived-token" },
        maximum_duration_seconds: 180,
        confirmation_expires_at: "2026-10-25T00:00:00Z",
      }),
    ),
  );

  await expect(
    authorizeConversationSession("", undefined, "TEXT"),
  ).rejects.toBeInstanceOf(ConversationApiError);
});
