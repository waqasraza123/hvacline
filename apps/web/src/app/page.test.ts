import { createElement } from "react";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync, writeFileSync } from "node:fs";
import { expect, it, vi } from "vitest";
import Home from "./page";

vi.mock("@/components/header-account", () => ({ HeaderAccount: () => null }));
vi.mock("@/features/billing/pricing", () => ({ Pricing: () => null }));
vi.mock("@/features/homepage-chat/homepage-chat", () => ({
  HomepageChat: () => null,
}));
vi.mock("@/features/outbound-demo/outbound-demo", () => ({
  OutboundDemo: () => null,
}));
vi.mock("@/features/outbound-demo/outbound-demo-dialog", () => ({
  OutboundDemoDialog: ({ children }: { children: ReactNode }) => children,
  OutboundDemoTrigger: ({ children }: { children: ReactNode }) =>
    createElement("button", null, children),
}));

it("renders the memory preview beside existing hero badges without changing the heading or primary action", () => {
  const html = renderToStaticMarkup(createElement(Home));
  expect(html).toContain("Stop losing jobs");
  expect(html).toContain("to missed calls.");
  expect(html).toMatch(/href="\/book"[^>]*>[\s\S]*?Try Voice Chat/);
  expect(html).toContain("<strong>Persistent Memory</strong>");
  expect(html).toContain("Customer-controlled · Preview");
  expect(html).toContain(
    'aria-label="Voice, memory, account and payment features"',
  );
  const css = readFileSync(new URL("./product.css", import.meta.url), "utf8");
  expect(css).toMatch(/\.hero-trust-badges\s*\{[^}]*flex-wrap:\s*wrap/s);
  expect(css).toMatch(/\.hero-trust-badge\s*\{[^}]*max-width:\s*100%/s);
  if (process.env.HVACLINE_HERO_PREVIEW_PATH) {
    const globalCss = readFileSync(
      new URL("./styles.css", import.meta.url),
      "utf8",
    );
    const hero = html.match(
      /<section class="product-hero[\s\S]*?<\/section>/,
    )?.[0];
    writeFileSync(
      process.env.HVACLINE_HERO_PREVIEW_PATH,
      `<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>${globalCss}\n${css}</style></head><body class="product-site">${hero}</body></html>`,
    );
  }
});
