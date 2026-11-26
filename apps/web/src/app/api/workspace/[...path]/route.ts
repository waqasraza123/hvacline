import { NextRequest } from "next/server";
import { handleWorkspace } from "@/features/workspace/proxy";

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return handleWorkspace(request, (await context.params).path.join("/"));
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
