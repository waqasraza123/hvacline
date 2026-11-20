import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { CustomerBackendError } from "./server";
import { proxyFailure, requestBody } from "./proxy";

const UUID =
  "[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}";
const PUBLIC_POSTS = new Set(["auth/login", "auth/signup"]);
const GET_PATHS = [
  /^auth\/(me|mfa\/status)$/,
  /^appointments$/,
  /^booking-limits$/,
  new RegExp(`^appointments/${UUID}$`),
];
const POST_PATHS = [
  /^auth\/(logout|mfa\/(setup|verify|recover|cancel))$/,
  /^conversation-sessions$/,
  /^conversation-intakes$/,
  new RegExp(`^appointments/${UUID}/(availability|reschedule)$`),
  new RegExp(`^conversation-sessions/${UUID}/(end|approved-faq-lookup)$`),
  new RegExp(
    `^conversation-sessions/${UUID}/booking/(intake-readback|availability|reservations|hazard)$`,
  ),
  new RegExp(
    `^conversation-sessions/${UUID}/booking/appointments/${UUID}/(confirm|release)$`,
  ),
];

export function mobilePathAllowed(path: string, method: string): boolean {
  return method === "GET"
    ? GET_PATHS.some((pattern) => pattern.test(path))
    : method === "POST" &&
        (PUBLIC_POSTS.has(path) ||
          POST_PATHS.some((pattern) => pattern.test(path)));
}

export async function proxyMobileRequest(
  request: NextRequest,
  segments: string[],
) {
  try {
    if (process.env.MOBILE_API_ENABLED !== "true")
      throw new CustomerBackendError(404, "Mobile access is not available.");
    const path = segments.join("/");
    if (
      request.nextUrl.search ||
      segments.some((segment) => !/^[a-zA-Z0-9-]+$/.test(segment)) ||
      !mobilePathAllowed(path, request.method)
    )
      throw new CustomerBackendError(
        404,
        "This mobile action is not available.",
      );
    if (request.headers.has("origin") || request.headers.get("sec-fetch-site"))
      throw new CustomerBackendError(
        403,
        "Use the mobile app for this action.",
      );
    const authorization = request.headers.get("authorization");
    const publicRequest = request.method === "POST" && PUBLIC_POSTS.has(path);
    if (
      !publicRequest &&
      !/^Bearer [A-Za-z0-9_-]{32,128}$/.test(authorization ?? "")
    )
      throw new CustomerBackendError(401, "Please sign in again.");
    const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL;
    const portalSecret = process.env.CUSTOMER_PORTAL_SECRET;
    if (!rawBase || !portalSecret || portalSecret.length < 32)
      throw new CustomerBackendError(
        503,
        "Mobile access is not configured yet.",
      );
    const base = new URL(rawBase);
    if (
      !["https:", "http:"].includes(base.protocol) ||
      (process.env.NODE_ENV === "production" && base.protocol !== "https:") ||
      base.username ||
      base.password ||
      base.search ||
      base.hash ||
      base.pathname !== "/"
    )
      throw new CustomerBackendError(
        503,
        "Mobile access is not configured correctly.",
      );
    const key = request.headers.get("idempotency-key");
    if (key && !/^[A-Za-z0-9_.:-]{1,128}$/.test(key))
      throw new CustomerBackendError(400, "The request reference is invalid.");
    if (path === "conversation-intakes" && !key)
      throw new CustomerBackendError(400, "The request reference is required.");
    const body =
      request.method === "POST" ? await requestBody(request) : undefined;
    const upstream = await fetch(`${base.origin}/api/v1/customer/${path}`, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        "X-Customer-Portal-Key": portalSecret,
        ...(!publicRequest && authorization
          ? { Authorization: authorization }
          : {}),
        ...(key ? { "Idempotency-Key": key } : {}),
      },
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(20_000),
    });
    const headers = {
      "Cache-Control": "no-store, private",
      Pragma: "no-cache",
      "X-Content-Type-Options": "nosniff",
    };
    if (upstream.status === 204)
      return new NextResponse(null, { status: 204, headers });
    if (!upstream.headers.get("content-type")?.includes("application/json"))
      throw new CustomerBackendError(
        502,
        "The mobile service could not respond.",
      );
    const data: unknown = await upstream.json();
    return NextResponse.json(data, {
      status: upstream.status,
      headers: {
        ...headers,
        ...(upstream.headers.get("idempotent-replayed") === "true"
          ? { "Idempotent-Replayed": "true" }
          : {}),
      },
    });
  } catch (error) {
    return proxyFailure(error);
  }
}
