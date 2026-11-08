import { LoadingSpinner } from "@/components/loading-spinner";
import "../product.css";

export default function LoadingPricing() {
  return (
    <div className="product-site">
      <main className="product-container" style={{ paddingBlock: "5rem" }}>
        <LoadingSpinner label="Loading maintenance packages…" />
      </main>
    </div>
  );
}
