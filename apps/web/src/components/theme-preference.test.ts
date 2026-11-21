import { afterEach, beforeEach, expect, it, vi } from "vitest";

let theme: typeof import("./theme-preference");
let stored: Map<string, string>;
let unsubscribe: (() => void)[];

beforeEach(async () => {
  vi.resetModules();
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 10, 20, 12));
  stored = new Map();
  unsubscribe = [];
  const storage = {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => stored.set(key, value),
  };
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal(
    "window",
    Object.assign(new EventTarget(), {
      localStorage: storage,
      setInterval,
      clearInterval,
    }),
  );
  vi.stubGlobal(
    "document",
    Object.assign(new EventTarget(), {
      documentElement: { dataset: {} },
    }),
  );
  theme = await import("./theme-preference");
});

afterEach(() => {
  unsubscribe.forEach((stop) => stop());
  vi.restoreAllMocks();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it.each([
  { hour: 6, minute: 59, expected: "dark" },
  { hour: 7, minute: 0, expected: "light" },
  { hour: 18, minute: 59, expected: "light" },
  { hour: 19, minute: 0, expected: "dark" },
  { hour: 0, minute: 0, expected: "dark" },
])(
  "uses local time at $hour:$minute for first paint and live updates",
  ({ hour, minute, expected }) => {
    vi.setSystemTime(new Date(2026, 10, 20, hour, minute));
    expect(theme.scheduledTheme()).toBe(expected);
    new Function(theme.themeInitializationScript)();
    expect(theme.currentTheme()).toBe(expected);
    unsubscribe.push(theme.subscribeToTheme(vi.fn()));
    expect(theme.currentTheme()).toBe(expected);
  },
);

it("switches an open page at the next minute after the local day boundary", () => {
  vi.setSystemTime(new Date(2026, 10, 20, 6, 59));
  const changed = vi.fn();
  unsubscribe.push(theme.subscribeToTheme(changed));
  expect(theme.currentTheme()).toBe("dark");
  changed.mockClear();
  vi.advanceTimersByTime(60_000);
  expect(theme.currentTheme()).toBe("light");
  expect(changed).toHaveBeenCalledOnce();
});

it("keeps a manual choice on reload but expires it at the next night boundary", () => {
  vi.setSystemTime(new Date(2026, 10, 20, 18, 59));
  unsubscribe.push(theme.subscribeToTheme(vi.fn()));
  theme.changeTheme("dark");
  new Function(theme.themeInitializationScript)();
  expect(theme.currentTheme()).toBe("dark");
  theme.changeTheme("light");
  vi.advanceTimersByTime(60_000);
  expect(theme.currentTheme()).toBe("dark");
  new Function(theme.themeInitializationScript)();
  expect(theme.currentTheme()).toBe("dark");
});

it("expires an overnight override the following morning", () => {
  vi.setSystemTime(new Date(2026, 10, 20, 23));
  unsubscribe.push(theme.subscribeToTheme(vi.fn()));
  theme.changeTheme("dark");
  vi.setSystemTime(new Date(2026, 10, 21, 7));
  window.dispatchEvent(new Event("focus"));
  expect(theme.currentTheme()).toBe("light");
});

it.each([
  "light",
  "dark",
  "broken",
  '{"theme":"dark","expiresAt":"later"}',
])(
  "returns legacy or invalid stored preference %s to automatic mode",
  (saved) => {
    stored.set("hvacline-theme", saved);
    new Function(theme.themeInitializationScript)();
    expect(theme.currentTheme()).toBe("light");
    unsubscribe.push(theme.subscribeToTheme(vi.fn()));
    expect(theme.currentTheme()).toBe("light");
  },
);

it("refreshes after sleep or a device clock change without waiting for a timer", () => {
  unsubscribe.push(theme.subscribeToTheme(vi.fn()));
  vi.setSystemTime(new Date(2026, 10, 20, 21));
  document.dispatchEvent(new Event("visibilitychange"));
  expect(theme.currentTheme()).toBe("dark");
  vi.setSystemTime(new Date(2026, 10, 21, 9));
  window.dispatchEvent(new Event("focus"));
  expect(theme.currentTheme()).toBe("light");
});

it("synchronizes stored choices and their removal between tabs", () => {
  unsubscribe.push(theme.subscribeToTheme(vi.fn()));
  stored.set(
    "hvacline-theme",
    JSON.stringify({
      theme: "dark",
      expiresAt: new Date(2026, 10, 20, 19).getTime(),
    }),
  );
  const event = new Event("storage");
  Object.defineProperty(event, "key", { value: "hvacline-theme" });
  window.dispatchEvent(event);
  expect(theme.currentTheme()).toBe("dark");
  stored.delete("hvacline-theme");
  window.dispatchEvent(event);
  expect(theme.currentTheme()).toBe("light");
});

it("shares one timer across controls and releases it after the last unsubscribe", () => {
  const first = theme.subscribeToTheme(vi.fn());
  const second = theme.subscribeToTheme(vi.fn());
  unsubscribe.push(first, second);
  expect(vi.getTimerCount()).toBe(1);
  first();
  expect(vi.getTimerCount()).toBe(1);
  second();
  expect(vi.getTimerCount()).toBe(0);
});

it("keeps manual and scheduled changes usable when storage is blocked", () => {
  vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
    throw new Error("Storage unavailable");
  });
  vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
    throw new Error("Storage unavailable");
  });
  new Function(theme.themeInitializationScript)();
  unsubscribe.push(theme.subscribeToTheme(vi.fn()));
  theme.changeTheme("dark");
  expect(theme.currentTheme()).toBe("dark");
  vi.setSystemTime(new Date(2026, 10, 21, 8));
  window.dispatchEvent(new Event("focus"));
  expect(theme.currentTheme()).toBe("light");
});
