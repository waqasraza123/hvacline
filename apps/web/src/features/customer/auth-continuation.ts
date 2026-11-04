export type AuthIntent = "demo-call" | undefined;

export type AuthPageProps = {
  searchParams: Promise<{ intent?: string | string[] }>;
};

export function parseAuthIntent(value: unknown): AuthIntent {
  return value === "demo-call" ? "demo-call" : undefined;
}

export function authPageHref(
  path: "/login" | "/signup" | "/mfa",
  intent?: AuthIntent,
): string {
  return intent === "demo-call" ? `${path}?intent=demo-call` : path;
}

export function authReturnHref(intent?: AuthIntent): string {
  return intent === "demo-call" ? "/?demo_call=1" : "/book";
}
