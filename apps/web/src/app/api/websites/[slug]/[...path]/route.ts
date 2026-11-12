import { NextRequest } from "next/server";
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

type Context = { params: Promise<{ slug: string; path: string[] }> };
export async function POST(request: NextRequest, context: Context) {
  try {
    requireSameOrigin(request);
    const { slug, path } = await context.params;
    const action = path.join("/");
    if (
      !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ||
      slug.length > 64 ||
      !(
        /^(conversation-sessions|conversation-intakes)$/.test(action) ||
        /^conversation-sessions\/[a-f0-9-]{36}\/(end|approved-faq-lookup)$/.test(
          action,
        )
      )
    )
      throw new CustomerBackendError(
        404,
        "This website action is not available.",
      );
    const body = await requestBody(request);
    const upstream = await customerBackend(
      `websites/${slug}/${action}`,
      "POST",
      body,
      request.headers.get("Idempotency-Key") ?? undefined,
    );
    return forwardResponse(upstream, await upstream.text());
  } catch (error) {
    return proxyFailure(error);
  }
}
