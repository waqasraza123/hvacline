"use client";

import { useSyncExternalStore } from "react";
import { ProductIcon } from "./product-icons";
import {
  changeTheme,
  currentTheme,
  serverTheme,
  subscribeToTheme,
} from "./theme-preference";
import styles from "./theme-toggle.module.css";

export function ThemeToggle() {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    currentTheme,
    serverTheme,
  );
  const dark = theme === "dark";

  return (
    <button
      className={styles.toggle}
      type="button"
      role="switch"
      aria-label="Dark mode"
      aria-checked={dark}
      title={`Switch to ${dark ? "light" : "dark"} mode`}
      onClick={() => changeTheme(dark ? "light" : "dark")}
    >
      <span className={styles.track} aria-hidden="true">
        <span className={styles.thumb} />
        <ProductIcon name="sun" className={styles.sun} />
        <ProductIcon name="moon" className={styles.moon} />
      </span>
    </button>
  );
}
