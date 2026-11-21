import { afterEach, describe, expect, it, vi } from "vitest";

import {
  listApprovedFaqs,
  createApprovedFaq,
  parseApprovedFaq,
  parseApprovedFaqLookup,
} from "./api";

describe("approved FAQ API parsing", () => {
  it("parses versioned FAQ and source-backed lookup responses", () => {
    const faq = parseApprovedFaq({
      id: "faq-1",
      agency_id: "agency-1",
      question: "What are your hours?",
      approved_answer: "Weekdays from 9 AM to 5 PM.",
      status: "ACTIVE",
      row_version: 3,
      created_at: "2026-08-08T00:00:00Z",
      updated_at: "2026-08-08T00:00:00Z",
    });
    const lookup = parseApprovedFaqLookup({
      matched: true,
      answer: faq.approvedAnswer,
      fallback_message: "A service team member will follow up.",
      source: {
        faq_id: faq.id,
        question: faq.question,
        row_version: faq.rowVersion,
      },
    });

    expect(faq.status).toBe("ACTIVE");
    expect(faq.questionVariations).toEqual([]);
    expect(lookup.source?.faqId).toBe("faq-1");
    expect(lookup.answer).toBe("Weekdays from 9 AM to 5 PM.");
  });

  it("rejects a matched response without a source", () => {
    expect(() =>
      parseApprovedFaqLookup({
        matched: true,
        answer: "Unsupported answer",
        fallback_message: "Human follow-up required.",
        source: null,
      }),
    ).toThrow("invalid data");
  });

  it("rejects an unmatched response carrying an unapproved partial answer", () => {
    expect(() =>
      parseApprovedFaqLookup({
        matched: false,
        answer: "Unapproved",
        source: null,
        fallback_message: "Ask staff.",
      }),
    ).toThrow("invalid data");
  });
});

afterEach(() => vi.unstubAllGlobals());

it("sends the hosted admin token in a header for embedded knowledge editing", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  await listApprovedFaqs("https://api.example.com", "synthetic-admin-token");
  expect(fetcher).toHaveBeenCalledWith(
    "https://api.example.com/api/v1/development/approved-faqs",
    expect.objectContaining({
      headers: { "X-Demo-Admin-Token": "synthetic-admin-token" },
      cache: "no-store",
    }),
  );
});

it("creates inactive answers with cleaned alternate questions", async () => {
  const response = {
    id: "faq-1",
    agency_id: "agency-1",
    question: "Office hours?",
    approved_answer: "Synthetic hours.",
    question_variations: ["When are you open?"],
    status: "INACTIVE",
    row_version: 1,
    created_at: "2026-11-09T00:00:00Z",
    updated_at: "2026-11-09T00:00:00Z",
  };
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(response), { status: 201 }));
  vi.stubGlobal("fetch", fetcher);
  const result = await createApprovedFaq("https://api.example.com", {
    question: " Office hours? ",
    approvedAnswer: " Synthetic hours. ",
    questionVariations: [" When are you open? ", ""],
  });
  expect(result.questionVariations).toEqual(["When are you open?"]);
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    question: "Office hours?",
    approved_answer: "Synthetic hours.",
    question_variations: ["When are you open?"],
    status: "INACTIVE",
  });
  expect(() =>
    parseApprovedFaq({ ...response, question_variations: [null] }),
  ).toThrow("invalid data");
  expect(() => parseApprovedFaq({ ...response, row_version: 0 })).toThrow(
    "invalid data",
  );
});
