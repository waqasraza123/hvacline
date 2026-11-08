import { LoadingSpinner } from "@/components/loading-spinner";

export default function LoadingPricing() {
  return (
    <main className="product-container" style={{ paddingBlock: "5rem" }}>
      <LoadingSpinner label="Loading maintenance packages…" />
    </main>
  );
}
