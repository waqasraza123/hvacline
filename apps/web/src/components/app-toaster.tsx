"use client";

import { useSyncExternalStore } from "react";
import { Toaster } from "sonner";
import { currentTheme, serverTheme, subscribeToTheme } from "./theme-preference";
import styles from "./app-toaster.module.css";

export function AppToaster() {
  const theme = useSyncExternalStore(subscribeToTheme, currentTheme, serverTheme);
  return <Toaster theme={theme} position="bottom-right" richColors closeButton
    toastOptions={{ classNames: { toast: styles.toast, title: styles.title } }} />;
}
