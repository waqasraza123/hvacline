"use client";

import Link from "next/link";
import styles from "./account-avatar.module.css";

export function accountInitials(fullName: string): string {
  const initials = fullName
    .trim()
    .split(/\s+/u)
    .map((part) => part.match(/[\p{L}\p{N}]/u)?.[0])
    .filter((initial): initial is string => initial !== undefined);
  if (!initials.length) return "?";
  const selected =
    initials.length === 1
      ? initials
      : [initials[0], initials[initials.length - 1]];
  return selected
    .map((initial) => Array.from(initial.toUpperCase())[0])
    .join("");
}

export function AccountAvatar({
  fullName,
  disabled = false,
}: {
  fullName: string;
  disabled?: boolean;
}) {
  const name = fullName.trim();
  return (
    <Link
      className={styles.avatar}
      href="/book"
      aria-label={name ? `Open account for ${name}` : "Open your account"}
      title={name ? `${name} · My account` : "My account"}
      aria-disabled={disabled || undefined}
      tabIndex={disabled ? -1 : undefined}
      onClick={(event) => {
        if (disabled) event.preventDefault();
      }}
    >
      <span aria-hidden="true">{accountInitials(fullName)}</span>
    </Link>
  );
}

export function AccountAvatarPlaceholder() {
  return <span className={styles.placeholder} aria-hidden="true" />;
}
