import { NextRequest } from "next/server";
import { proxyMobileRequest } from "@/features/customer/mobile-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context) {
  return proxyMobileRequest(request, (await context.params).path);
}

export { handle as GET, handle as POST };
