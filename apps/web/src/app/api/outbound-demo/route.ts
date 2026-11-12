import { createHmac, randomBytes } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { requireSameOrigin } from "@/features/customer/proxy";
import { currentCustomer } from "@/features/customer/server";
import {
  isDemoCall,
  isSmsChallenge,
  scenarios,
  UUID_PATTERN,
} from "@/features/outbound-demo/contracts";

const COOKIE =
  process.env.NODE_ENV === "production"
    ? "__Host-hvacline-call-visitor"
    : "hvacline-call-visitor";
const TOKEN = /^[A-Za-z0-9_-]{43}$/;

function json(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

function rejected(message: string, status: number, code?: string) {
  return json(
    {
      error: { message, ...(code ? { code } : {}) },
      request_not_created: true,
    },
    status,
  );
}

async function customerGate(
  creating = false,
): Promise<{ customerId: string } | { denied: NextResponse }> {
  const customer = await currentCustomer();
  if (customer.status === "authenticated")
    return { customerId: customer.user.id };
  const anonymous = customer.status === "anonymous";
  return {
    denied: json(
      {
        error: {
          code: anonymous
            ? "CALLBACK_SIGN_IN_REQUIRED"
            : "CALLBACK_AUTH_UNAVAILABLE",
          message: anonymous
            ? "Sign in to request a demo call or check its status."
            : "We couldn’t check your sign-in. Please try again.",
        },
        ...(creating ? { request_not_created: true } : {}),
      },
      anonymous ? 401 : 503,
    ),
  };
}

async function backend(path: string, customerId: string, body?: string) {
  const secret = process.env.OUTBOUND_DEMO_SECRET;
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!secret || secret.length < 32 || !raw) throw new Error("Unavailable");
  const owner = createHmac("sha256", secret)
    .update("hvacline/outbound-customer/v1\0")
    .update(customerId)
    .digest("base64url");
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
  return fetch(
    `${url.toString().replace(/\/$/, "")}/api/v1/outbound-demo/${path}`,
    {
      method: body === undefined ? "GET" : "POST",
      body,
      cache: "no-store",
      redirect: "error",
      headers: {
        "Content-Type": "application/json",
        "X-Outbound-Demo-Key": secret,
        "X-Outbound-Visitor": owner,
      },
      signal: AbortSignal.timeout(40_000),
    },
  );
}

async function phoneVerification(
  data: Record<string, unknown>,
  customerId: string,
) {
  const sending = data.action === "send_code";
  const keys = sending
    ? ["action", "phone_number", "sms_consent", "sms_consent_version"]
    : ["action", "challenge_id", "code"];
  if (
    (!sending && data.action !== "verify_code") ||
    Object.keys(data).some((key) => !keys.includes(key)) ||
    (sending
      ? typeof data.phone_number !== "string" ||
        !/^\+1[0-9]{10}$/.test(data.phone_number) ||
        data.sms_consent !== true ||
        data.sms_consent_version !== "outbound-sms-v1"
      : typeof data.challenge_id !== "string" ||
        !UUID_PATTERN.test(data.challenge_id) ||
        typeof data.code !== "string" ||
        !/^[0-9]{6}$/.test(data.code))
  )
    return rejected(
      "Check your phone number, text consent and verification code.",
      400,
    );
  try {
    const payload = sending
      ? {
          phone_number: data.phone_number,
          sms_consent: true,
          sms_consent_version: data.sms_consent_version,
        }
      : { challenge_id: data.challenge_id, code: data.code };
    const response = await backend(
      sending ? "phone-verifications" : "phone-verifications/verify",
      customerId,
      JSON.stringify(payload),
    );
    const value: unknown = await response.json();
    if (!response.ok) {
      const messages: Record<number, string> = {
        403: "Start again with a new verification code.",
        422: sending
          ? "Use a US phone number that can receive text messages."
          : "That code is invalid or expired. Check the text and try again.",
        429: "The text verification limit has been reached. Please try later.",
      };
      return json(
        {
          error: {
            message:
              messages[response.status] ??
              "Text verification is unavailable. Please try again later.",
          },
        },
        response.status,
      );
    }
    if (!isSmsChallenge(value)) throw new Error("Invalid response");
    return json(value);
  } catch {
    return json(
      {
        error: {
          message:
            "Text verification is unconfirmed. Wait a minute before requesting another code.",
        },
      },
      503,
    );
  }
}

export async function GET(request: NextRequest) {
  if (request.headers.get("sec-fetch-site") === "cross-site")
    return json({ available: false }, 403);
  const gate = await customerGate();
  if ("denied" in gate) return gate.denied;
  const requestId = request.nextUrl.searchParams.get("request_id");
  const existing = request.cookies.get(COOKIE)?.value;
  if (
    requestId &&
    (!UUID_PATTERN.test(requestId) || !existing || !TOKEN.test(existing))
  ) {
    return json(
      {
        error: {
          message:
            "This call request could not be found. Contact the demo owner before retrying.",
        },
      },
      400,
    );
  }
  if (!requestId && process.env.OUTBOUND_DEMO_FORM_ENABLED !== "true")
    return json({ available: false });
  const token =
    existing && TOKEN.test(existing)
      ? existing
      : randomBytes(32).toString("base64url");
  try {
    const upstream = await backend(
      requestId ? `requests/${requestId}` : "availability",
      gate.customerId,
    );
    const value: unknown = await upstream.json();
    if (!upstream.ok)
      return json(
        {
          error: {
            message:
              "Call status is unavailable. Contact the demo owner before requesting another call.",
          },
        },
        upstream.status,
      );
    if (
      requestId
        ? !isDemoCall(value)
        : typeof value !== "object" ||
          value === null ||
          !("available" in value) ||
          typeof value.available !== "boolean"
    )
      throw new Error("Invalid response");
    const response = json(value);
    if (token !== existing)
      response.cookies.set(COOKIE, token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        path: "/",
        maxAge: 24 * 60 * 60,
      });
    return response;
  } catch {
    return requestId
      ? json(
          {
            error: {
              message:
                "The call outcome is unconfirmed. Contact the demo owner before retrying.",
            },
          },
          503,
        )
      : json({ available: false });
  }
}

export async function POST(request: NextRequest) {
  try {
    requireSameOrigin(request);
  } catch {
    return rejected("Please use the demo form on this website.", 403);
  }
  const gate = await customerGate(true);
  if ("denied" in gate) return gate.denied;
  if (process.env.OUTBOUND_DEMO_FORM_ENABLED !== "true")
    return rejected(
      "Phone demos aren’t available right now. Please try browser Voice.",
      503,
    );
  const token = request.cookies.get(COOKIE)?.value;
  if (!token || !TOKEN.test(token))
    return rejected(
      "Allow cookies, then reload to check calling availability.",
      409,
    );
  if (!request.headers.get("content-type")?.startsWith("application/json"))
    return rejected("Please send the demo form again.", 415);
  try {
    const reader = request.body?.getReader();
    if (!reader) throw new Error("Invalid body");
    let size = 0;
    const chunks: Uint8Array[] = [];
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2048) {
        await reader.cancel();
        return rejected("The demo form is too large.", 413);
      }
      chunks.push(value);
    }
    const data: unknown = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    if (typeof data === "object" && data !== null && "action" in data)
      return phoneVerification(
        data as Record<string, unknown>,
        gate.customerId,
      );
    if (
      typeof data !== "object" ||
      data === null ||
      !("request_id" in data) ||
      typeof data.request_id !== "string" ||
      !UUID_PATTERN.test(data.request_id) ||
      !("phone_number" in data) ||
      typeof data.phone_number !== "string" ||
      !/^\+[1-9][0-9]{7,14}$/.test(data.phone_number) ||
      !("scenario" in data) ||
      typeof data.scenario !== "string" ||
      !Object.hasOwn(scenarios, data.scenario) ||
      !("consent" in data) ||
      data.consent !== true ||
      !("consent_version" in data) ||
      data.consent_version !== "outbound-demo-v1" ||
      !("phone_verification_id" in data) ||
      typeof data.phone_verification_id !== "string" ||
      !UUID_PATTERN.test(data.phone_verification_id) ||
      Object.keys(data).some(
        (key) =>
          ![
            "request_id",
            "phone_number",
            "scenario",
            "consent",
            "consent_version",
            "phone_verification_id",
          ].includes(key),
      )
    )
      return rejected(
        "Verify your US phone number, choose a scenario and agree to one AI demo call.",
        400,
      );
    const upstream = await backend(
      "calls",
      gate.customerId,
      JSON.stringify(data),
    );
    const result: unknown = await upstream.json();
    if (!upstream.ok) {
      const code =
        typeof result === "object" &&
        result !== null &&
        "error" in result &&
        typeof result.error === "object" &&
        result.error !== null &&
        "code" in result.error
          ? result.error.code
          : null;
      if (upstream.status === 403 && code === "DEMO_NUMBER_NOT_AUTHORIZED")
        return rejected(
          "This private demo is limited to numbers approved by the demo owner.",
          403,
        );
      if (upstream.status === 429 && code === "DEMO_CALL_LIMIT")
        return rejected(
          "The demo call limit has been reached. Please try browser Voice.",
          429,
        );
      if (upstream.status === 422 && code === "DEMO_PHONE_NUMBER_INVALID")
        return rejected("Enter a valid US phone number.", 422);
      if (upstream.status === 422 && code === "DEMO_DESTINATION_UNSUPPORTED")
        return rejected(
          "Only US mobile, landline and internet phone numbers are supported.",
          422,
        );
      if (
        upstream.status === 403 &&
        code === "DEMO_PHONE_VERIFICATION_REQUIRED"
      )
        return rejected(
          "Verify your phone number with a new text-message code first.",
          403,
          code,
        );
      const message =
        upstream.status === 403
          ? "This private demo is limited to numbers approved by the demo owner."
          : upstream.status === 429
            ? "The demo call limit has been reached. Please try browser Voice."
            : "The call outcome is unconfirmed. Contact the demo owner before retrying.";
      return json({ error: { message } }, upstream.status);
    }
    if (!isDemoCall(result)) throw new Error("Invalid response");
    return json(result);
  } catch {
    return json(
      {
        error: {
          message:
            "The call outcome is unconfirmed. Check its status before requesting another call.",
        },
      },
      503,
    );
  }
}
