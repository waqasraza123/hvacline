"use client";

import { useEffect, useId, useRef } from "react";
import styles from "./memory.module.css";

export type MemoryAction = {
  title: string;
  description: string;
  label: string;
  path: string;
  fields?: Record<string, unknown>;
};

export function MemoryActionDialog({
  action,
  busy,
  onClose,
  onConfirm,
}: {
  action: MemoryAction;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const title = useId();
  const description = useId();

  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    element?.showModal();
    cancel.current?.focus();
    document.body.style.overflow = "hidden";
    return () => {
      element?.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected)
        previousFocus.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className={styles.confirmation}
      aria-labelledby={title}
      aria-describedby={description}
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <h3 id={title}>{action.title}</h3>
      <p id={description}>{action.description}</p>
      <div className={styles.confirmActions}>
        <button
          ref={cancel}
          type="button"
          className={styles.secondary}
          disabled={busy}
          onClick={onClose}
        >
          Keep as is
        </button>
        <button
          type="button"
          className={styles.dangerButton}
          disabled={busy}
          onClick={onConfirm}
        >
          {busy ? "Updating…" : action.label}
        </button>
      </div>
    </dialog>
  );
}
