import { OperationsWorkspace } from "@/features/operations/workspace";
import { parsePublicEnvironment } from "@/lib/environment";

export const metadata = { title: "Multilingual AI Voice · Interactive Demo" };

export default function MultilingualVoicePage() {
  const environment = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ? parsePublicEnvironment(process.env) : null;
  return <OperationsWorkspace apiBaseUrl={environment?.apiBaseUrl ?? ""}
    conversationAiEnabled={environment?.conversationAiEnabled ?? false}
    initialSection="multilingual" backendConfigured={environment !== null} />;
}
