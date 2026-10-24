import { NextRequest, NextResponse } from "next/server";
import { CustomerBackendError } from "./server";

export function requireSameOrigin(request: NextRequest) {
  if (
    request.headers.get("origin") !== request.nextUrl.origin ||
    request.headers.get("sec-fetch-site") === "cross-site"
  ) {
    throw new CustomerBackendError(
      403,
      "Please use the booking form on this website.",
    );
  }
}

export async function requestBody(request: NextRequest): Promise<string> {
  if (!request.headers.get("content-type")?.startsWith("application/json"))
    throw new CustomerBackendError(415, "Please send the form again.");
  const body = await request.text();
  if (body.length > 65_536)
    throw new CustomerBackendError(
      413,
      "This conversation is too long to save. Please start a shorter conversation.",
    );
  try {
    JSON.parse(body);
  } catch {
    throw new CustomerBackendError(
      400,
      "The form could not be read. Please try again.",
    );
  }
  return body;
}

export function proxyFailure(error: unknown) {
  const status = error instanceof CustomerBackendError ? error.status : 503;
  const message =
    error instanceof CustomerBackendError
      ? error.message
      : "Booking is temporarily unavailable. Please try again shortly.";
  return NextResponse.json(
    { error: { message } },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

export function forwardResponse(response: Response, body: string) {
  if (
    response.status !== 204 &&
    !response.headers.get("content-type")?.includes("application/json")
  ) {
    return proxyFailure(
      new CustomerBackendError(
        502,
        "Booking is temporarily unavailable. Please try again shortly.",
      ),
    );
  }
  return new NextResponse(response.status === 204 ? null : body, {
    status: response.status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...(response.headers.has("Idempotent-Replayed")
        ? {
            "Idempotent-Replayed": response.headers.get("Idempotent-Replayed")!,
          }
        : {}),
      ...(response.headers.has("Retry-After")
        ? { "Retry-After": response.headers.get("Retry-After")! }
        : {}),
    },
  });
}
