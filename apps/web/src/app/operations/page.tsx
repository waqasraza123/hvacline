import { OperationsWorkspace } from "@/features/operations/workspace";
import { parsePublicEnvironment } from "@/lib/environment";
export const metadata = { title: "Operations dashboard" };
export default function OperationsPage() {
  const environment = parsePublicEnvironment(process.env);
  return (
    <OperationsWorkspace
      apiBaseUrl={environment.apiBaseUrl}
      conversationAiEnabled={environment.conversationAiEnabled}
    />
  );
}
