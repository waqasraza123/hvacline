import { OperationsWorkspace } from "@/features/operations/workspace";
import { parsePublicEnvironment } from "@/lib/environment";

export const metadata = { title: "AI Lead Recovery · Interactive Demo" };

export default async function LeadRecoveryPage({
  searchParams,
}: {
  searchParams: Promise<{ setup?: string }>;
}) {
  const environment = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
    ? parsePublicEnvironment(process.env)
    : null;
  const parameters = await searchParams;

  return (
    <OperationsWorkspace
      apiBaseUrl={environment?.apiBaseUrl ?? ""}
      conversationAiEnabled={environment?.conversationAiEnabled ?? false}
      initialSection="recovery"
      initialSetup={parameters.setup === "1" && environment !== null}
      backendConfigured={environment !== null}
    />
  );
}
