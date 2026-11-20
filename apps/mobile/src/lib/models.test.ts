import { afterEach, describe, expect, it, vi } from "vitest";
import {
  authorization,
  challenge,
  login,
  storedSession,
  appointments,
} from "./models";

const id = "00000000-0000-4000-8000-000000000001";
const token = "fictional-customer-session-token-for-mobile-tests";
afterEach(() => {
  vi.useRealTimers();
});

describe("mobile session contracts", () => {
  it("never accepts a password-only full session", () => {
    expect(() =>
      challenge({ session_token: token, expires_in: 28800 }),
    ).toThrow();
    expect(() =>
      login(
        {
          session_token: token,
          user: {
            id,
            email: "fictional@example.test",
            full_name: "Fictional Customer",
          },
          expires_in: 28800,
        },
        "https://hvacline.example",
      ),
    ).toThrow();
  });
  it("binds a stored session to its server and enforces expiry", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-20T00:00:00Z"));
    const session = {
      token,
      origin: "https://hvacline.example",
      expiresAt: Date.now() + 1000,
    };
    expect(storedSession(session, session.origin)).toEqual(session);
    expect(storedSession(session, "https://other.example")).toBeUndefined();
    vi.advanceTimersByTime(1001);
    expect(storedSession(session, session.origin)).toBeUndefined();
  });
  it("does not accept session tokens in MFA challenge responses", () => {
    expect(() =>
      challenge({
        mfa_required: true,
        next_action: "verify",
        challenge_token: token,
        expires_in: 600,
        session_token: token,
      }),
    ).toThrow();
  });
});

describe("mobile conversation grants", () => {
  const grant = (mode: "VOICE" | "TEXT") => ({
    session_id: id,
    input_mode: mode,
    connection: {
      provider: "elevenlabs",
      transport: mode === "VOICE" ? "webrtc" : "websocket",
      credential:
        mode === "VOICE"
          ? "fictional-one-use-voice-grant"
          : "wss://api.elevenlabs.io/v1/convai/conversation?conversation_signature=fictional",
    },
    maximum_duration_seconds: 180,
    authorization_expires_at: new Date(Date.now() + 180000).toISOString(),
    confirmation_expires_at: new Date(Date.now() + 180000).toISOString(),
  });
  it("requires the selected mode and its matching transport", () => {
    expect(authorization(grant("VOICE"), "VOICE").transport).toBe("webrtc");
    expect(authorization(grant("TEXT"), "TEXT").transport).toBe("websocket");
    expect(() => authorization(grant("VOICE"), "TEXT")).toThrow();
    expect(() =>
      authorization(
        {
          ...grant("TEXT"),
          connection: { ...grant("TEXT").connection, transport: "webrtc" },
        },
        "TEXT",
      ),
    ).toThrow();
  });
  it.each([
    "ws://api.elevenlabs.io/v1/convai/conversation",
    "wss://untrusted.example/v1/convai/conversation",
    "wss://api.elevenlabs.io/unexpected",
    "wss://api.elevenlabs.io:444/v1/convai/conversation",
  ])("rejects signed URLs outside the approved endpoint: %s", (credential) => {
    expect(() =>
      authorization(
        {
          ...grant("TEXT"),
          connection: { ...grant("TEXT").connection, credential },
        },
        "TEXT",
      ),
    ).toThrow();
  });
  it("rejects expired grants and invalid appointment states", () => {
    expect(() =>
      authorization(
        {
          ...grant("VOICE"),
          authorization_expires_at: new Date(Date.now() - 1000).toISOString(),
        },
        "VOICE",
      ),
    ).toThrow();
    expect(() =>
      appointments({ appointments: [{ status: "UNKNOWN" }], timezone: "UTC" }),
    ).toThrow();
  });
});
