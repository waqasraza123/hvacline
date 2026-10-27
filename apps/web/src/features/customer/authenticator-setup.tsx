"use client";

import { QRCodeSVG } from "qrcode.react";
import type { MfaSetup } from "./mfa-setup";
import styles from "./mfa-form.module.css";

export function AuthenticatorSetup({ setup }: { setup: MfaSetup }) {
  return (
    <div className={styles.setup}>
      <div className={styles.scanPanel}>
        <div className={styles.qr}>
          <QRCodeSVG
            value={setup.otpauthUri}
            size={208}
            level="M"
            marginSize={4}
            bgColor="#ffffff"
            fgColor="#18181b"
            role="img"
            title="Scan to add HVACLine AI to your authenticator"
          />
        </div>
        <div className={styles.scanInstructions}>
          <span className={styles.smallLabel}>START WITH A SCAN</span>
          <h2>Open your authenticator app.</h2>
          <p>
            In Google Authenticator, Microsoft Authenticator, or another
            compatible app, choose <strong>Add account</strong>, then{" "}
            <strong>Scan QR code</strong>.
          </p>
          <p>
            Your app will create a six-digit code for HVACLine AI. On the same
            phone? Use manual setup below.
          </p>
        </div>
      </div>
      <details className={styles.manual}>
        <summary>
          Can’t scan? Enter a setup key instead{" "}
          <span aria-hidden="true">+</span>
        </summary>
        <div className={styles.manualContent}>
          <p>
            Choose manual entry in your app. Use <strong>HVACLine AI</strong> as
            the account name and select a <strong>time-based</strong> key.
          </p>
          <code aria-label="Authenticator setup key">{setup.secret}</code>
          <p>Keep this key private, just like your password.</p>
        </div>
      </details>
    </div>
  );
}
