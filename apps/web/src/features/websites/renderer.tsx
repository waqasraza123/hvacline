import type { ComponentType } from "react";
import type { ResolvedWebsite, TemplateId } from "./contracts";
import { WebsiteFrame } from "./primitives";
import { IndustrialWebsite } from "./layouts/industrial";
import { EditorialWebsite } from "./layouts/editorial";
import { CalmWebsite } from "./layouts/calm";

const templateComponents = {
  industrial: IndustrialWebsite,
  editorial: EditorialWebsite,
  calm: CalmWebsite,
} satisfies Record<TemplateId, ComponentType<{ site: ResolvedWebsite }>>;

export function WebsiteRenderer({ site }: { site: ResolvedWebsite }) {
  const Template = templateComponents[site.template.id];
  return (
    <WebsiteFrame site={site}>
      <Template site={site} />
    </WebsiteFrame>
  );
}
