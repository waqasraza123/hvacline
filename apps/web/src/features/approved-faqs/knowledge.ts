import type {
  ApprovedFaq,
  ApprovedFaqDraft,
  ApprovedFaqStatus,
} from "./contracts";

export type KnowledgeFilter = "ALL" | ApprovedFaqStatus;

export function cleanFaqDraft(draft: ApprovedFaqDraft): ApprovedFaqDraft {
  return {
    question: draft.question.trim(),
    approvedAnswer: draft.approvedAnswer.trim(),
    questionVariations: draft.questionVariations
      .map((question) => question.trim())
      .filter(Boolean),
  };
}

export function faqDraftProblem(draft: ApprovedFaqDraft): string | undefined {
  const cleaned = cleanFaqDraft(draft);
  if (!cleaned.question || !cleaned.approvedAnswer)
    return "Enter a question and its approved answer.";
  if (cleaned.question.length > 300 || cleaned.approvedAnswer.length > 2000)
    return "Use up to 300 characters for the question and 2,000 for the answer.";
  if (cleaned.questionVariations.length > 8)
    return "Add up to eight alternate questions, one per line.";
  const questions = [cleaned.question, ...cleaned.questionVariations].map(
    (question) =>
      question
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, " ")
        .trim(),
  );
  if (questions.some((question) => !question))
    return "Each question must contain letters or numbers.";
  if (cleaned.questionVariations.some((question) => question.length > 300))
    return "Each alternate question can contain up to 300 characters.";
  if (new Set(questions).size !== questions.length)
    return "Use distinct alternate questions, different from the main question.";
  return undefined;
}

export function faqDraftChanged(faq: ApprovedFaq, draft: ApprovedFaqDraft) {
  const cleaned = cleanFaqDraft(draft);
  return (
    cleaned.question !== faq.question ||
    cleaned.approvedAnswer !== faq.approvedAnswer ||
    JSON.stringify(cleaned.questionVariations) !==
      JSON.stringify(faq.questionVariations)
  );
}

export function matchesKnowledgeFilter(
  faq: ApprovedFaq,
  search: string,
  status: KnowledgeFilter,
): boolean {
  if (status !== "ALL" && faq.status !== status) return false;
  const terms = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const text = [faq.question, faq.approvedAnswer, ...faq.questionVariations]
    .join(" ")
    .toLowerCase();
  return terms.every((term) => text.includes(term));
}
