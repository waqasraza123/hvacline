import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { SettingsTabs } from "./settings-tabs";

it("keeps both settings panels mounted with linked tab semantics", () => {
  const html = renderToStaticMarkup(createElement(SettingsTabs, {
    label: "Agent configuration",
    tabs: [
      { key: "general", label: "General", content: createElement("input", { defaultValue: "Unsaved agency draft" }) },
      { key: "voice", label: "Voice", content: createElement("input", { defaultValue: "Unsaved voice draft" }) },
    ],
  }));
  expect(html).toContain('role="tablist" aria-label="Agent configuration"');
  expect(html).toContain('aria-selected="true"');
  expect(html).toContain('aria-selected="false"');
  expect(html).toContain('value="Unsaved agency draft"');
  expect(html).toContain('value="Unsaved voice draft"');
  const panels = [...html.matchAll(/<div\b[^>]*role="tabpanel"[^>]*>/g)].map((match) => match[0]);
  expect(panels).toHaveLength(2);
  expect(panels[0]).not.toContain("hidden=");
  expect(panels[1]).toContain('hidden=""');
  for (const panel of panels) {
    const id = panel.match(/\bid="([^"]+)"/)?.[1];
    const label = panel.match(/aria-labelledby="([^"]+)"/)?.[1];
    expect(id).toBeDefined();
    expect(label).toBeDefined();
    expect(html).toContain(`aria-controls="${id}"`);
    expect(html).toContain(`id="${label}"`);
  }
});
