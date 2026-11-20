import type { ConversationSpeaker, ConversationTurn } from "./contracts";

export function appendTranscript(
  current: readonly ConversationTurn[],
  speaker: ConversationSpeaker,
  text: string,
): ConversationTurn[] {
  const normalizedText = text.trim();
  const lastTurn = current.at(-1);
  if (lastTurn?.speaker === speaker) {
    if (lastTurn.text === normalizedText) {
      return [...current];
    }
    if (
      normalizedText.startsWith(lastTurn.text) ||
      lastTurn.text.startsWith(normalizedText)
    ) {
      return [...current.slice(0, -1), { speaker, text: normalizedText }];
    }
  }
  return [...current, { speaker, text: normalizedText }];
}
