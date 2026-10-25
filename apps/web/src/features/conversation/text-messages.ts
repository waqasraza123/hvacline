export const MAX_MESSAGE_CHARACTERS = 2_000;
const ECHO_LIFETIME_MILLISECONDS = 30_000;
const MAX_PENDING_ECHOES = 60;

export function customerMessage(value: string): string {
  const text = value.trim();
  if (!text || text.length > MAX_MESSAGE_CHARACTERS) {
    throw new Error("Enter a message between 1 and 2,000 characters.");
  }
  return text;
}

export class PendingTextEchoes {
  private pending: { text: string; expiresAt: number }[] = [];

  add(text: string, now = Date.now()) {
    this.pending = this.pending
      .filter((item) => item.expiresAt > now)
      .slice(-(MAX_PENDING_ECHOES - 1));
    this.pending.push({ text, expiresAt: now + ECHO_LIFETIME_MILLISECONDS });
  }

  consume(text: string, now = Date.now()): boolean {
    this.pending = this.pending.filter((item) => item.expiresAt > now);
    const index = this.pending.findIndex((item) => item.text === text.trim());
    if (index < 0) return false;
    this.pending.splice(index, 1);
    return true;
  }

  clear() {
    this.pending = [];
  }
}
