import type { ConversationSessionAuthorization } from "./contracts";

type SessionConnection =
  | { signedUrl: string; connectionType: "websocket"; textOnly: true }
  | { conversationToken: string; connectionType: "webrtc"; textOnly: false };

export function sessionConnection({
  inputMode,
  transport,
  credential,
  provider,
}: Pick<
  ConversationSessionAuthorization,
  "inputMode" | "transport" | "credential" | "provider"
>): SessionConnection {
  if (provider === "local") {
    throw new Error("Local conversations require the local adapter.");
  }
  if (inputMode === "TEXT" && transport === "websocket") {
    return {
      signedUrl: credential,
      connectionType: "websocket",
      textOnly: true,
    };
  }
  if (inputMode === "VOICE" && transport === "webrtc") {
    return {
      conversationToken: credential,
      connectionType: "webrtc",
      textOnly: false,
    };
  }
  throw new Error(
    "The connection does not match the selected conversation mode.",
  );
}
