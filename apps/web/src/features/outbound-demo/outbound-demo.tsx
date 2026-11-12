import Link from "next/link";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";
import { OutboundDemoTrigger } from "./outbound-demo-dialog";

export function OutboundDemo() {
  return (
    <section
      id="call-me"
      className="outbound-demo product-container"
      aria-labelledby="outbound-title"
    >
      <div className="outbound-demo-intro">
        <p className="product-eyebrow">ON YOUR PHONE</p>
        <h2 id="outbound-title">
          Inbound &amp;
          <br />
          <span>outbound calling.</span>
        </h2>
        <p>
          Call Line from your phone, or have Line call you. Natural HVAC
          conversations, with the same AI receptionist.
        </p>
        <div className="outbound-demo-voice" aria-hidden="true">
          <VoiceSymbol />
          <span>Line · AI receptionist</span>
        </div>
      </div>
      <div className="calling-preview">
        <div className="calling-preview-label">
          <ProductIcon name="clock" />
          <span>One AI conversation · up to 3 minutes</span>
        </div>
        <article>
          <ProductIcon name="phone" />
          <div>
            <h3>Inbound calling</h3>
            <p>Pick up your phone and speak with Line about your HVAC needs.</p>
          </div>
        </article>
        <article>
          <ProductIcon name="phone" />
          <div>
            <h3>Outbound calling</h3>
            <p>
              Try the AI voice agent on your own phone with a short HVAC demo.
            </p>
          </div>
        </article>
        <OutboundDemoTrigger />
        <Link className="outbound-demo-browser" href="/book">
          Try browser Voice today <span aria-hidden="true">↗</span>
        </Link>
      </div>
    </section>
  );
}
