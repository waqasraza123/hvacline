import { NextRequest, NextResponse } from "next/server";
import { CustomerBackendError } from "@/features/customer/server";
import { forwardResponse, proxyFailure, requestBody, requireSameOrigin } from "@/features/customer/proxy";
import { parsePublicEnvironment } from "@/lib/environment";

const cookieName = "hvacline-recovery";
type Context = { params: Promise<{ path?: string[] }> };

async function backend(path: string, token: string, method: string, body?: string) {
  const environment = parsePublicEnvironment(process.env);
  return fetch(`${environment.apiBaseUrl}/api/v1/recovery/continuation${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body,
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(20000),
  });
}

async function handle(request: NextRequest, context: Context) {
  try {
    const path = (await context.params).path?.join("/") ?? "";
    if (request.method === "POST") requireSameOrigin(request);
    if (path === "exchange" && request.method === "POST") {
      const value: unknown = JSON.parse(await requestBody(request));
      const token = value && typeof value === "object" && "token" in value ? value.token : null;
      if (typeof token !== "string" || !/^[a-f0-9]{32}\.[a-f0-9]{64}$/.test(token))
        throw new CustomerBackendError(403, "This booking link is invalid or expired.");
      const result = await backend("", token, "GET");
      const response = forwardResponse(result, await result.text());
      if (result.ok) response.cookies.set(cookieName, token, {
        httpOnly: true, secure: request.nextUrl.protocol === "https:",
        sameSite: "strict", path: "/api/recovery", maxAge: 30 * 60,
      });
      return response;
    }
    if (path === "logout" && request.method === "POST") {
      const response = new NextResponse(null, { status: 204 });
      response.cookies.set(cookieName, "", { httpOnly: true, secure: request.nextUrl.protocol === "https:", sameSite: "strict", path: "/api/recovery", maxAge: 0 });
      return response;
    }
    const allowed = request.method === "GET" ? path === "" : ["availability", "reserve", "readback", "confirm", "release"].includes(path);
    if (!allowed) throw new CustomerBackendError(404, "This booking action is unavailable.");
    const token = request.cookies.get(cookieName)?.value;
    if (!token || !/^[a-f0-9]{32}\.[a-f0-9]{64}$/.test(token))
      throw new CustomerBackendError(403, "Open the booking link sent by the business to continue.");
    const body = request.method === "POST" ? await requestBody(request) : undefined;
    const result = await backend(path ? `/${path}` : "", token, request.method, body);
    return forwardResponse(result, await result.text());
  } catch (error) {
    return proxyFailure(error);
  }
}

export const GET = handle;
export const POST = handle;
