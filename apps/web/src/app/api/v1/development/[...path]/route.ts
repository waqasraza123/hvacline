import { NextRequest } from "next/server";
import {
  CustomerBackendError,
  customerBackend,
} from "@/features/customer/server";
import {
  forwardResponse,
  proxyFailure,
  requestBody,
  requireSameOrigin,
} from "@/features/customer/proxy";

const identifier = "[a-fA-F0-9-]{36}";
const postPaths = [
  /^conversation-sessions$/,
  /^conversation-intakes$/,
  new RegExp(`^conversation-sessions/${identifier}/(end|approved-faq-lookup)$`),
  new RegExp(
    `^conversation-sessions/${identifier}/booking/(intake-readback|hazard|availability|reservations)$`,
  ),
  new RegExp(
    `^conversation-sessions/${identifier}/booking/appointments/${identifier}/(confirm|release)$`,
  ),
  /^hvac\/(availability|reservations)$/,
  new RegExp(`^appointments/${identifier}/(availability|reschedule)$`),
  new RegExp(`^hvac/appointments/${identifier}/(confirm|release)$`),
];

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context) {
  try {
    const path = (await context.params).path.join("/");
    const allowed =
      request.method === "GET"
        ? ["receptionist-settings", "appointments"].includes(path) ||
          new RegExp(`^appointments/${identifier}$`).test(path)
        : postPaths.some((pattern) => pattern.test(path));
    if (!allowed)
      throw new CustomerBackendError(404, "This action is not available.");
    if (request.method === "POST") requireSameOrigin(request);
    const body =
      request.method === "POST" ? await requestBody(request) : undefined;
    const response = await customerBackend(
      path,
      request.method,
      body,
      request.headers.get("Idempotency-Key") ?? undefined,
    );
    return forwardResponse(response, await response.text());
  } catch (error) {
    return proxyFailure(error);
  }
}

export const GET = handle;
export const POST = handle;
