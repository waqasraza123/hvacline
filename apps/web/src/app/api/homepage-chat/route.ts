import { randomBytes } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { currentCustomer } from "@/features/customer/server";
import { requireSameOrigin } from "@/features/customer/proxy";

const COOKIE =
  process.env.NODE_ENV === "production"
    ? "__Host-hvacline-visitor"
    : "hvacline-visitor";
const TOKEN = /^[A-Za-z0-9_-]{43}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function json(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

async function backend(token: string, body?: string) {
  const secret = process.env.CUSTOMER_PORTAL_SECRET;
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!raw || !secret || secret.length < 32) throw new Error("Unavailable");
  const url = new URL(raw);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    (process.env.NODE_ENV === "production" && url.protocol !== "https:")
  )
    throw new Error("Unavailable");
  return fetch(`${url.toString().replace(/\/$/, "")}/api/v1/homepage-chat`, {
    method: body ? "POST" : "GET",
    body,
    cache: "no-store",
    redirect: "error",
    headers: {
      "Content-Type": "application/json",
      "X-Customer-Portal-Key": secret,
      "X-Homepage-Visitor": token,
    },
    signal: AbortSignal.timeout(30_000),
  });
}

export async function GET(request: NextRequest) {
  try {
    if (request.headers.get("sec-fetch-site") === "cross-site")
      return json({ state: "unavailable" }, 403);
    const customer = await currentCustomer();
    if (customer.status === "authenticated")
      return json({ state: "authenticated", remaining: 0 });
    if (customer.status === "unavailable")
      return json({ state: "unavailable", remaining: 0 }, 503);
    const existing = request.cookies.get(COOKIE)?.value;
    const token =
      existing && TOKEN.test(existing)
        ? existing
        : randomBytes(32).toString("base64url");
    const upstream = await backend(token);
    if (!upstream.ok) return json({ state: "unavailable", remaining: 0 }, 503);
    const data: unknown = await upstream.json();
    if (
      typeof data !== "object" ||
      data === null ||
      !("state" in data) ||
      typeof data.state !== "string" ||
      !["ready", "used", "busy"].includes(data.state) ||
      !("remaining" in data) ||
      data.remaining !== (data.state === "ready" ? 1 : 0)
    )
      throw new Error("Invalid status");
    const response = json({ state: data.state, remaining: data.remaining });
    if (token !== existing)
      response.cookies.set(COOKIE, token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 24 * 60 * 60,
      });
    return response;
  } catch {
    return json({ state: "unavailable", remaining: 0 }, 503);
  }
}

export async function POST(request: NextRequest) {
  try {
    requireSameOrigin(request);
  } catch {
    return json(
      { error: { message: "Please use Line on this website." } },
      403,
    );
  }
  try {
    if (!request.headers.get("content-type")?.startsWith("application/json"))
      return json(
        { error: { message: "Please send your message again." } },
        415,
      );
    const raw = await request.text();
    if (raw.length > 8192)
      return json(
        {
          error: {
            message: "Please keep your message under 1,000 characters.",
          },
        },
        413,
      );
    let data: unknown;
    try {
      data = JSON.parse(raw);
    } catch {
      return json(
        {
          error: {
            message: "Your message could not be read. Please send it again.",
          },
        },
        400,
      );
    }
    if (
      typeof data !== "object" ||
      data === null ||
      !("message" in data) ||
      typeof data.message !== "string" ||
      !data.message.trim() ||
      data.message.length > 1000 ||
      !("request_id" in data) ||
      typeof data.request_id !== "string" ||
      !UUID.test(data.request_id) ||
      !("ai_disclosure_accepted" in data) ||
      data.ai_disclosure_accepted !== true
    ) {
      return json(
        {
          error: {
            message:
              "Enter a message of up to 1,000 characters and accept AI processing.",
          },
        },
        400,
      );
    }
    const customer = await currentCustomer();
    if (customer.status === "authenticated")
      return json({ state: "authenticated" }, 409);
    if (customer.status === "unavailable")
      return json(
        {
          error: {
            message: "Your account could not be checked. Please retry.",
          },
        },
        503,
      );
    const token = request.cookies.get(COOKIE)?.value;
    if (!token || !TOKEN.test(token))
      return json(
        {
          error: { message: "Allow cookies or sign in to continue with Line." },
        },
        409,
      );
    const upstream = await backend(
      token,
      JSON.stringify({
        message: data.message.trim(),
        request_id: data.request_id,
        ai_disclosure_accepted: true,
      }),
    );
    const result: unknown = await upstream.json();
    if (typeof result !== "object" || result === null)
      throw new Error("Invalid reply");
    if (!upstream.ok) {
      const error =
        "error" in result &&
        typeof result.error === "object" &&
        result.error !== null
          ? result.error
          : {};
      return json(
        {
          error: {
            message:
              "message" in error && typeof error.message === "string"
                ? error.message
                : "Line couldn’t finish. Please retry or sign in.",
            code:
              "code" in error && typeof error.code === "string"
                ? error.code
                : "HOMEPAGE_CHAT_UNAVAILABLE",
          },
        },
        upstream.status,
      );
    }
    if (
      !("reply" in result) ||
      typeof result.reply !== "string" ||
      !result.reply.trim() ||
      result.reply.length > 4000 ||
      !("remaining" in result) ||
      result.remaining !== 0
    )
      throw new Error("Invalid reply");
    return json({ reply: result.reply, remaining: 0 });
  } catch {
    return json(
      {
        error: {
          message:
            "Line’s connection was interrupted. Your message is kept; check availability before retrying.",
        },
      },
      503,
    );
  }
}
