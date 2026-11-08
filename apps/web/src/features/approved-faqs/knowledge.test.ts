import { describe, expect, it } from "vitest";
import {
  cleanFaqDraft,
  faqDraftChanged,
  faqDraftProblem,
  matchesKnowledgeFilter,
} from "./knowledge";
import type { ApprovedFaq } from "./contracts";

const faq: ApprovedFaq = {
  id: "faq-1",
  agencyId: "agency-1",
  question: "Can I request air conditioning repair?",
  approvedAnswer: "Staff can assess the equipment.",
  questionVariations: ["Can you help with AC repair?"],
  status: "ACTIVE",
  rowVersion: 1,
  createdAt: "2026-11-09T00:00:00Z",
  updatedAt: "2026-11-09T00:00:00Z",
};

describe("knowledge editing", () => {
  it("finds alternate phrasings and answer text while respecting status", () => {
    expect(matchesKnowledgeFilter(faq, "AC repair", "ACTIVE")).toBe(true);
    expect(matchesKnowledgeFilter(faq, "assess equipment", "ALL")).toBe(true);
    expect(matchesKnowledgeFilter(faq, "AC repair", "INACTIVE")).toBe(false);
    expect(matchesKnowledgeFilter(faq, "financing", "ALL")).toBe(false);
  });
  it("distinguishes unsaved answer and variation changes from whitespace", () => {
    expect(
      faqDraftChanged(faq, { ...faq, question: ` ${faq.question} ` }),
    ).toBe(false);
    expect(
      faqDraftChanged(faq, { ...faq, approvedAnswer: "A changed answer." }),
    ).toBe(true);
    expect(faqDraftChanged(faq, { ...faq, questionVariations: [] })).toBe(true);
    expect(
      cleanFaqDraft({
        ...faq,
        questionVariations: [" When are you open? ", ""],
      }).questionVariations,
    ).toEqual(["When are you open?"]);
  });
  it("requires distinct bounded questions before saving", () => {
    expect(faqDraftProblem(faq)).toBeUndefined();
    expect(
      faqDraftProblem({ ...faq, questionVariations: [faq.question] }),
    ).toContain("distinct");
    expect(faqDraftProblem({ ...faq, questionVariations: ["???"] })).toContain(
      "letters",
    );
    expect(
      faqDraftProblem({ ...faq, questionVariations: Array(9).fill("Other?") }),
    ).toContain("eight");
  });
});
