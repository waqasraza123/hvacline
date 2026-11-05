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

export async function requestBody(
  request: Pick<NextRequest, "headers" | "body">,
): Promise<string> {
  if (!request.headers.get("content-type")?.startsWith("application/json"))
    throw new CustomerBackendError(415, "Please send the form again.");
  const reader = request.body?.getReader();
  if (!reader) throw new CustomerBackendError(400, "The form could not be read.");
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 65_536) {
      await reader.cancel();
      throw new CustomerBackendError(413, "This request is too large. Send a smaller form.");
    }
    chunks.push(value);
  }
  const body = Buffer.concat(chunks).toString("utf8");
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
