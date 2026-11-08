export type AuthIntent = "demo-call" | "billing" | undefined;

export type AuthPageProps = {
  searchParams: Promise<{ intent?: string | string[] }>;
};

export function parseAuthIntent(value: unknown): AuthIntent {
  return value === "demo-call" || value === "billing" ? value : undefined;
}

export function authPageHref(
  path: "/login" | "/signup" | "/mfa",
  intent?: AuthIntent,
): string {
  return intent ? `${path}?intent=${intent}` : path;
}

export function authReturnHref(intent?: AuthIntent): string {
  return intent === "demo-call"
    ? "/?demo_call=1"
    : intent === "billing"
      ? "/billing"
      : "/book";
}
