export type AuthIntent =
  "demo-call" | "billing" | `website:${string}` | undefined;

export type AuthPageProps = {
  searchParams: Promise<{ intent?: string | string[] }>;
};

export function parseAuthIntent(value: unknown): AuthIntent {
  if (
    typeof value === "string" &&
    /^website:[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) &&
    value.length <= 72
  )
    return value as `website:${string}`;
  return value === "demo-call" || value === "billing" ? value : undefined;
}

export function authPageHref(
  path: "/login" | "/signup" | "/mfa",
  intent?: AuthIntent,
): string {
  return intent ? `${path}?intent=${intent}` : path;
}

export function authReturnHref(intent?: AuthIntent): string {
  if (intent?.startsWith("website:") && parseAuthIntent(intent))
    return `/sites/${intent.slice(8)}`;
  return intent === "demo-call"
    ? "/?demo_call=1"
    : intent === "billing"
      ? "/billing"
      : "/book";
}
