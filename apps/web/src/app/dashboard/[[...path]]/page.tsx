import { notFound } from "next/navigation";
import { OperationsWorkspace } from "@/features/operations/workspace";
import { resolveOperationsPath, sections, subpages } from "@/features/operations/dashboard-navigation";
import { parsePublicEnvironment } from "@/lib/environment";

type RouteProps = { params: Promise<{ path?: string[] }> };

export async function generateMetadata({ params }: RouteProps) {
  const { path = [] } = await params;
  const destination = resolveOperationsPath(`/dashboard/${path.join("/")}`);
  const label = sections.find((item) => item.key === destination?.section)?.label;
  const child = subpages.find((item) => item.section === destination?.section && item.key === destination?.subpage);
  return { title: label ? `${child ? `${child.label} · ` : ""}${label} · Dashboard` : "Dashboard" };
}

export default async function OperationsPage({ params }: RouteProps) {
  const { path = [] } = await params;
  const destination = resolveOperationsPath(`/dashboard/${path.join("/")}`);
  if (!destination) notFound();
  const environment = parsePublicEnvironment(process.env);
  if (destination.section === "browser voice" && !environment.conversationAiEnabled) notFound();
  return <OperationsWorkspace apiBaseUrl={environment.apiBaseUrl}
    initialSection={destination.section} conversationAiEnabled={environment.conversationAiEnabled} />;
}
