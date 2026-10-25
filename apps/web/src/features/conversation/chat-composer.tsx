"use client";

import { useId, useState } from "react";
import type { FormEvent } from "react";
import { ProductIcon } from "@/components/product-icons";
import { customerMessage, MAX_MESSAGE_CHARACTERS } from "./text-messages";
import styles from "./conversation-chat.module.css";

export function ChatComposer({
  send,
  connected,
  onTyping,
  textOnly,
}: {
  send: (text: string) => void;
  connected: boolean;
  onTyping: () => void;
  textOnly: boolean;
}) {
  const id = useId();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!connected) return;
    try {
      send(customerMessage(message));
      setMessage("");
      setError("");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Your message could not be sent. Please try again.",
      );
    }
  }

  return (
    <form className={styles.composer} onSubmit={submit}>
      <label className={styles.label} htmlFor={id}>
        Message Line
      </label>
      <div className={styles.inputRow}>
        <textarea
          id={id}
          aria-describedby={`${id}-help`}
          className={styles.input}
          maxLength={MAX_MESSAGE_CHARACTERS}
          onChange={(event) => {
            setMessage(event.target.value);
            if (connected) onTyping();
          }}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Type your message…"
          rows={2}
          value={message}
        />
        <button
          aria-label="Send message"
          className={styles.send}
          disabled={!connected || !message.trim()}
          type="submit"
        >
          <ProductIcon name="arrow" />
          Send
        </button>
      </div>
      <p className={styles.help} id={`${id}-help`}>
        {!connected
          ? "Start a conversation above to enable Send. Your unsent message stays here."
          : textOnly
            ? "Chat is silent. Your microphone stays off."
            : "You can type while using voice. Line will still speak its replies."}{" "}
        Shift + Enter adds a new line.
      </p>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
