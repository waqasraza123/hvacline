import { LoadingSpinner } from "@/components/loading-spinner";
import "../product.css";

export default function LoadingBilling() {
  return (
    <div className="product-site">
      <main className="product-container" style={{ paddingBlock: "5rem" }}>
        <LoadingSpinner label="Opening your maintenance account…" />
      </main>
    </div>
  );
}
