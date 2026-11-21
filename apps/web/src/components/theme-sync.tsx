"use client";

import { useEffect } from "react";
import { subscribeToTheme } from "./theme-preference";

export function ThemeSync() {
  useEffect(() => subscribeToTheme(() => {}), []);
  return null;
}
