import { expect, it } from "vitest";
import { operationsHref, resolveOperationsPath, sections, subpages } from "./dashboard-navigation";

it("round trips every section and child to a unique direct URL", () => {
  const paths = sections.map((item) => {
    const href = operationsHref(item.key);
    expect(resolveOperationsPath(href)).toEqual({ section: item.key });
    expect(resolveOperationsPath(`${href}/`)).toEqual({ section: item.key });
    return href;
  });
  for (const item of subpages) {
    const href = operationsHref(item.section, item.key);
    expect(resolveOperationsPath(href)).toEqual({ section: item.section, subpage: item.key });
    paths.push(href);
  }
  expect(new Set(paths).size).toBe(paths.length);
});

it("rejects unknown, partial and mismatched child paths", () => {
  for (const path of ["/dashboard/unknown", "/dashboard/calls/voice", "/dashboard/integrations", "/dashboard/scheduling/rules/extra", "/dashboard-other", "/operations", "/operations/calls", "/workspace"]) {
    expect(resolveOperationsPath(path)).toBeNull();
  }
});
