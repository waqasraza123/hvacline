import { permanentRedirect } from "next/navigation";

export default async function LegacyLeadRecoveryPage({
  searchParams,
}: {
  searchParams: Promise<{ setup?: string }>;
}) {
  const parameters = await searchParams;
  permanentRedirect(
    parameters.setup === "1"
      ? "/ai-lead-recovery?setup=1"
      : "/ai-lead-recovery",
  );
}
