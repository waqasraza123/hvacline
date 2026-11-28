import { describe, expect, it } from "vitest";
import { forwardResponse, requestBody } from "./proxy";

describe("customer request body limits", () => {
  it("reads a valid JSON body split across chunks", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array<ArrayBuffer>>({
      start(controller) {
        controller.enqueue(encoder.encode('{"code":'));
        controller.enqueue(encoder.encode('"123456"}'));
        controller.close();
      },
    });
    expect(
      await requestBody({
        headers: new Headers({ "Content-Type": "application/json" }),
        body,
      }),
    ).toBe('{"code":"123456"}');
  });

  it("stops an oversized stream before reading its remaining body", async () => {
    let cancelled = false;
    let reads = 0;
    const body = new ReadableStream<Uint8Array<ArrayBuffer>>({
      pull(controller) {
        reads += 1;
        controller.enqueue(new Uint8Array(65_537));
      },
      cancel() {
        cancelled = true;
      },
    });
    await expect(
      requestBody({
        headers: new Headers({ "Content-Type": "application/json" }),
        body,
      }),
    ).rejects.toMatchObject({ status: 413 });
    expect(cancelled).toBe(true);
    expect(reads).toBeLessThanOrEqual(2);
  });
});

it("forwards only allowlisted provider notification metadata", () => {
  const upstream = new Response(null, { status: 424, headers: {
    "X-External-Failures": JSON.stringify([
      { provider: "stripe", kind: "billing", private_detail: "must-not-forward" },
      { provider: "unknown", kind: "access" },
    ]),
    "Idempotent-Replayed": "true",
  } });
  const result = forwardResponse(upstream, '{"error":{"code":"STRIPE_UNAVAILABLE"}}');
  expect(result.status).toBe(424);
  expect(result.headers.get("X-External-Failures")).toBe('[{"provider":"stripe","kind":"billing"}]');
  expect(result.headers.get("Idempotent-Replayed")).toBe("true");
});
