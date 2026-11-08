export type Theme = "light" | "dark";

const STORAGE_KEY = "hvacline-theme";
const CHANGE_EVENT = "hvacline-theme-change";
const SYSTEM_THEME = "(prefers-color-scheme: dark)";
let preference: Theme | null | undefined;

function savedTheme(): Theme | null {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : null;
  } catch {
    return null;
  }
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function serverTheme(): Theme {
  return "light";
}

export function changeTheme(theme: Theme) {
  preference = theme;
  applyTheme(theme);
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    window.dispatchEvent(new Event(CHANGE_EVENT));
    return;
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function subscribeToTheme(onChange: () => void) {
  preference ??= savedTheme();
  const system = window.matchMedia(SYSTEM_THEME);

  function refreshTheme() {
    applyTheme(preference ?? (system.matches ? "dark" : "light"));
    onChange();
  }

  function onSystemChange() {
    if (preference === null) refreshTheme();
  }

  function onStorage(event: StorageEvent) {
    if (event.key !== STORAGE_KEY && event.key !== null) return;
    preference = savedTheme();
    refreshTheme();
  }

  window.addEventListener(CHANGE_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  system.addEventListener("change", onSystemChange);
  refreshTheme();
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
    system.removeEventListener("change", onSystemChange);
  };
}

export const themeInitializationScript = `(()=>{let theme;try{const saved=localStorage.getItem(${JSON.stringify(STORAGE_KEY)});if(saved==="light"||saved==="dark")theme=saved}catch{}document.documentElement.dataset.theme=theme||(window.matchMedia(${JSON.stringify(SYSTEM_THEME)}).matches?"dark":"light")})()`;
