import { NextRequest, NextResponse } from "next/server";
import {
  CustomerBackendError,
  completeCustomerLogout,
  customerBackend,
  parseCustomer,
} from "@/features/customer/server";
import {
  forwardResponse,
  proxyFailure,
  requestBody,
  requireSameOrigin,
} from "@/features/customer/proxy";

type Context = { params: Promise<{ action: string }> };

async function handle(request: NextRequest, context: Context) {
  try {
    const { action } = await context.params;
    if (
      (request.method === "GET" && action !== "me") ||
      (request.method === "POST" &&
        !["signup", "login", "logout"].includes(action))
    )
      throw new CustomerBackendError(404, "Page not found.");
    if (request.method === "POST") requireSameOrigin(request);
    const body =
      request.method === "POST" ? await requestBody(request) : undefined;
    if (action === "logout") {
      const response = await completeCustomerLogout(
        customerBackend("auth/logout", request.method, body),
      );
      return response;
    }
    const upstream = await customerBackend(
      `auth/${action}`,
      request.method,
      body,
    );
    if (!upstream.ok) return forwardResponse(upstream, await upstream.text());
    const data: unknown = await upstream.json();
    if (action === "me")
      return NextResponse.json(parseCustomer(data), {
        headers: { "Cache-Control": "no-store" },
      });
    if (
      typeof data !== "object" ||
      data === null ||
      !("user" in data) ||
      !("session_token" in data) ||
      typeof data.session_token !== "string" ||
      data.session_token.length < 32 ||
      !("expires_in" in data) ||
      typeof data.expires_in !== "number" ||
      data.expires_in < 1 ||
      data.expires_in > 28800
    )
      throw new CustomerBackendError(
        502,
        "We could not finish signing you in. Please try again.",
      );
    const response = NextResponse.json(
      { user: parseCustomer(data.user) },
      { status: upstream.status, headers: { "Cache-Control": "no-store" } },
    );
    response.cookies.set(CUSTOMER_COOKIE, data.session_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: data.expires_in,
    });
    return response;
  } catch (error) {
    return proxyFailure(error);
  }
}

export const GET = handle;
export const POST = handle;
