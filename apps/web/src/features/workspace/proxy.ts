import { NextRequest, NextResponse } from "next/server";
import { CustomerBackendError } from "@/features/customer/server";
import { forwardResponse, proxyFailure, requestBody } from "@/features/customer/proxy";

export const WORKSPACE_COOKIE = process.env.NODE_ENV === "production" ? "__Host-hvacline-workspace" : "hvacline-workspace";
const id = "[a-fA-F0-9-]{36}";
const paths = {
  GET: [/^auth\/me$/, new RegExp(`^businesses/${id}/(setup|team|profile)$`), new RegExp(`^businesses/${id}/hvac/(operations|schedule)$`)],
  POST: [/^auth\/(login|logout|invitation\/(start|confirm|accept))$/, /^bootstrap\/(list|create)$/, new RegExp(`^bootstrap/businesses/${id}/owner-invitation$`), new RegExp(`^businesses/${id}/invitations$`), new RegExp(`^businesses/${id}/invitations/${id}/revoke$`), new RegExp(`^businesses/${id}/handoff-requests/${id}/status$`)],
  PUT: [new RegExp(`^businesses/${id}/members/${id}$`), new RegExp(`^businesses/${id}/(profile|hvac/schedule)$`)],
};

function backendBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw) throw new CustomerBackendError(503, "The staff workspace is not configured.");
  const url = new URL(raw);
  if (!["http:", "https:"].includes(url.protocol) || process.env.NODE_ENV === "production" && url.protocol !== "https:" || url.username || url.password || url.search || url.hash || !["", "/"].includes(url.pathname)) throw new CustomerBackendError(503, "The staff workspace backend is not configured correctly.");
  return url.origin;
}

function logoutResponse(): NextResponse {
  const response = new NextResponse(null, { status: 204, headers: { "Cache-Control": "no-store" } });
  response.cookies.set(WORKSPACE_COOKIE, "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: 0 });
  return response;
}

export async function handleWorkspace(request: NextRequest, path: string) {
  try {
    const method = request.method as keyof typeof paths;
    if (!paths[method]?.some((pattern) => pattern.test(path))) throw new CustomerBackendError(404, "This workspace action is not available.");
    if (method !== "GET" && (request.headers.get("origin") !== request.nextUrl.origin || request.headers.get("sec-fetch-site") === "cross-site")) throw new CustomerBackendError(403, "Use the staff workspace on this website.");
    const secret = process.env.WORKSPACE_PORTAL_SECRET;
    if (!secret || secret.length < 32) throw new CustomerBackendError(503, "The staff workspace is not configured.");
    let body = method === "GET" ? undefined : await requestBody(request);
    let upstreamPath = path;
    let upstreamMethod: string = method;
    const headers: Record<string, string> = { "Content-Type": "application/json", "X-Workspace-Portal-Key": secret };
    const session = request.cookies.get(WORKSPACE_COOKIE)?.value;
    if (session) headers.Authorization = `Bearer ${session}`;
    if (path.startsWith("bootstrap/")) {
      const data: unknown = JSON.parse(body ?? "{}");
      if (typeof data !== "object" || data === null || !("bootstrap_key" in data) || typeof data.bootstrap_key !== "string" || data.bootstrap_key.length < 32 || data.bootstrap_key.length > 256) throw new CustomerBackendError(403, "Enter the platform-owner access key.");
      const { bootstrap_key: key, ...rest } = data;
      headers["X-Workspace-Bootstrap-Key"] = key;
      if (path === "bootstrap/list") { upstreamPath = "bootstrap/businesses"; upstreamMethod = "GET"; body = undefined; }
      else { upstreamPath = path === "bootstrap/create" ? "bootstrap/businesses" : path; body = JSON.stringify(rest); }
    }
    const send = () => fetch(`${backendBase()}/api/v1/workspace/${upstreamPath}`, { method: upstreamMethod, body, headers, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(20000) });
    if (path === "auth/logout") {
      try { const upstream = await send(); if (!upstream.ok) return forwardResponse(upstream, await upstream.text()); }
      catch { throw new CustomerBackendError(503, "Sign-out could not be confirmed. Retry before leaving this shared device."); }
      return logoutResponse();
    }
    const upstream = await send();
    if (!upstream.ok) return forwardResponse(upstream, await upstream.text());
    if (path === "auth/login" || path === "auth/invitation/confirm") {
      const value: unknown = await upstream.json();
      if (typeof value !== "object" || value === null || !("session_token" in value) || typeof value.session_token !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(value.session_token) || !("mfa_verified" in value) || value.mfa_verified !== true || !("expires_in" in value) || typeof value.expires_in !== "number" || !Number.isInteger(value.expires_in) || value.expires_in < 1 || value.expires_in > 28800) throw new CustomerBackendError(502, "Staff sign-in could not be confirmed.");
      const response = NextResponse.json({ signed_in: true }, { headers: { "Cache-Control": "no-store" } });
      response.cookies.set(WORKSPACE_COOKIE, value.session_token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: value.expires_in });
      return response;
    }
    return forwardResponse(upstream, await upstream.text());
  } catch (failure) {
    if (failure instanceof CustomerBackendError) return proxyFailure(failure);
    return proxyFailure(new CustomerBackendError(503, "The staff workspace is temporarily unavailable. Refresh saved status before repeating a change."));
  }
}
