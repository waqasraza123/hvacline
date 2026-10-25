import { describe, expect, it } from "vitest";
import { sessionConnection } from "./connection";

describe("conversation connections", () => {
  it("uses the private signed socket URL for silent Chat", () => {
    const signedUrl =
      "wss://api.elevenlabs.io/v1/convai/conversation?conversation_signature=fictional";
    expect(
      sessionConnection({
        inputMode: "TEXT",
        transport: "websocket",
        credential: signedUrl,
      }),
    ).toEqual({
      signedUrl,
      connectionType: "websocket",
      textOnly: true,
    });
  });

  it("preserves WebRTC and speech for Voice", () => {
    expect(
      sessionConnection({
        inputMode: "VOICE",
        transport: "webrtc",
        credential: "voice-token",
      }),
    ).toEqual({
      conversationToken: "voice-token",
      connectionType: "webrtc",
      textOnly: false,
    });
  });

  it.each([
    ["TEXT", "webrtc"],
    ["VOICE", "websocket"],
  ] as const)(
    "never falls back from %s to an incompatible %s connection",
    (inputMode, transport) => {
      expect(() =>
        sessionConnection({ inputMode, transport, credential: "credential" }),
      ).toThrow("selected conversation mode");
    },
  );
});
