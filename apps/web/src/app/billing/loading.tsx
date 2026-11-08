import { LoadingSpinner } from "@/components/loading-spinner";

export default function LoadingBilling() {
  return (
    <main className="product-container" style={{ paddingBlock: "5rem" }}>
      <LoadingSpinner label="Opening your maintenance account…" />
    </main>
  );
}
