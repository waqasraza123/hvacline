export type Theme = "light" | "dark";

const STORAGE_KEY = "hvacline-theme";
const DAY_START_HOUR = 7;
const NIGHT_START_HOUR = 19;
type ThemePreference = { theme: Theme; expiresAt: number };
let preference: ThemePreference | null | undefined;
const listeners = new Set<() => void>();
let refreshInterval: number | undefined;

function savedTheme(): ThemePreference | null {
  try {
    const saved: unknown = JSON.parse(
      window.localStorage.getItem(STORAGE_KEY) ?? "null",
    );
    if (
      typeof saved !== "object" ||
      saved === null ||
      !("theme" in saved) ||
      !("expiresAt" in saved) ||
      (saved.theme !== "light" && saved.theme !== "dark") ||
      typeof saved.expiresAt !== "number" ||
      !Number.isFinite(saved.expiresAt) ||
      saved.expiresAt <= Date.now()
    )
      return null;
    return { theme: saved.theme, expiresAt: saved.expiresAt };
  } catch {
    return null;
  }
}

export function scheduledTheme(date = new Date()): Theme {
  const hour = date.getHours();
  return hour >= DAY_START_HOUR && hour < NIGHT_START_HOUR ? "light" : "dark";
}

function nextThemeChange(date: Date): number {
  const next = new Date(date);
  const hour = date.getHours();
  if (hour < DAY_START_HOUR) {
    next.setHours(DAY_START_HOUR, 0, 0, 0);
  } else if (hour < NIGHT_START_HOUR) {
    next.setHours(NIGHT_START_HOUR, 0, 0, 0);
  } else {
    next.setDate(next.getDate() + 1);
    next.setHours(DAY_START_HOUR, 0, 0, 0);
  }
  return next.getTime();
}

function refreshTheme() {
  const now = new Date();
  if (preference && preference.expiresAt <= now.getTime()) preference = null;
  const theme = preference?.theme ?? scheduledTheme(now);
  const changed = document.documentElement.dataset.theme !== theme;
  document.documentElement.dataset.theme = theme;
  if (changed) listeners.forEach((listener) => listener());
}

function onStorage(event: StorageEvent) {
  if (event.key !== STORAGE_KEY && event.key !== null) return;
  preference = savedTheme();
  refreshTheme();
}

export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function serverTheme(): Theme {
  return "light";
}

export function changeTheme(theme: Theme) {
  preference = { theme, expiresAt: nextThemeChange(new Date()) };
  refreshTheme();
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preference));
  } catch {
    return;
  }
}

export function subscribeToTheme(onChange: () => void) {
  if (listeners.size === 0) {
    preference ??= savedTheme();
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", refreshTheme);
    document.addEventListener("visibilitychange", refreshTheme);
    refreshInterval = window.setInterval(refreshTheme, 60_000);
  }
  listeners.add(onChange);
  refreshTheme();
  return () => {
    listeners.delete(onChange);
    if (listeners.size > 0) return;
    window.clearInterval(refreshInterval);
    refreshInterval = undefined;
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("focus", refreshTheme);
    document.removeEventListener("visibilitychange", refreshTheme);
  };
}

export const themeInitializationScript = `(()=>{let theme;try{const saved=JSON.parse(localStorage.getItem(${JSON.stringify(STORAGE_KEY)})||"null");if(saved&&(saved.theme==="light"||saved.theme==="dark")&&typeof saved.expiresAt==="number"&&Number.isFinite(saved.expiresAt)&&saved.expiresAt>Date.now())theme=saved.theme}catch{}const hour=new Date().getHours();document.documentElement.dataset.theme=theme||(hour>=${DAY_START_HOUR}&&hour<${NIGHT_START_HOUR}?"light":"dark")})()`;
