import { NextRequest, NextResponse } from "next/server";
import {
  customerBackend,
  CustomerBackendError,
} from "@/features/customer/server";
import {
  forwardResponse,
  proxyFailure,
  requestBody,
  requireSameOrigin,
} from "@/features/customer/proxy";

type Context = { params: Promise<{ path: string[] }> };
export const maxDuration = 60;

async function handle(request: NextRequest, context: Context) {
  try {
    const path = (await context.params).path.join("/");
    if (request.method === "GET" && path === "plans") {
      const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
      if (!raw)
        throw new CustomerBackendError(
          503,
          "Package pricing is not available yet.",
        );
      const base = new URL(raw);
      if (
        !["http:", "https:"].includes(base.protocol) ||
        base.username ||
        base.password ||
        base.search ||
        base.hash ||
        (process.env.NODE_ENV === "production" && base.protocol !== "https:")
      ) {
        throw new CustomerBackendError(
          503,
          "Package pricing is temporarily unavailable.",
        );
      }
      const response = await fetch(
        `${base.toString().replace(/\/$/, "")}/api/v1/billing/plans`,
        {
          cache: "no-store",
          redirect: "error",
          signal: AbortSignal.timeout(15_000),
        },
      );
      return forwardResponse(response, await response.text());
    }
    const allowed =
      request.method === "GET"
        ? ["status", "history"].includes(path)
        : ["checkout", "topup", "refresh", "portal"].includes(path) ||
          /^(topups|checkouts)\/[a-f0-9-]{36}\/cancel$/i.test(path);
    if (!allowed)
      return NextResponse.json(
        { error: { message: "This action is unavailable." } },
        { status: 404 },
      );
    if (request.method === "POST") requireSameOrigin(request);
    const body =
      request.method === "POST" ? await requestBody(request) : undefined;
    const response = await customerBackend(
      `billing/${path}`,
      request.method,
      body,
      undefined,
      "session",
      55_000,
    );
    return forwardResponse(response, await response.text());
  } catch (error) {
    return proxyFailure(error);
  }
}
export const GET = handle;
export const POST = handle;
