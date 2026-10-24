"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { Brand } from "@/components/brand";
import { ProductIcon, VoiceSymbol } from "@/components/product-icons";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const signup = mode === "signup";
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const fields = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/account/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: fields.get("email"),
          password: fields.get("password"),
          ...(signup
            ? {
                full_name: fields.get("full_name"),
                fictional_data_acknowledged:
                  fields.get("fictional_data_acknowledged") === "on",
              }
            : {}),
        }),
        signal: AbortSignal.timeout(20000),
      });
      if (!response.ok) {
        const body: unknown = await response.json();
        const message =
          typeof body === "object" &&
          body !== null &&
          "error" in body &&
          typeof body.error === "object" &&
          body.error !== null &&
          "message" in body.error &&
          typeof body.error.message === "string"
            ? body.error.message
            : "We couldn’t finish that. Check your details and try again.";
        throw new Error(message);
      }
      router.replace("/book");
      router.refresh();
    } catch (failure) {
      setError(
        failure instanceof Error &&
          failure.name !== "TimeoutError" &&
          failure.name !== "TypeError"
          ? failure.message
          : "We couldn’t connect. Please try again in a moment.",
      );
      setBusy(false);
    }
  }
  return (
    <div className="customer-shell auth-page">
      <header className="product-header product-container">
        <Brand />
        <Link className="product-text-link" href="/">
          Back to home <span>↗</span>
        </Link>
      </header>
      <main className="auth-layout product-container">
        <section className="auth-story">
          <p className="product-eyebrow">A BETTER WAY TO BOOK.</p>
          <h1>
            Your comfort.
            <br />
            <span>
              One conversation
              <br />
              away.
            </span>
          </h1>
          <p>
            A little less waiting. A lot less back-and-forth. Let’s find the
            right time for your home.
          </p>
          <div className="auth-line-mark">
            <span>
              <VoiceSymbol />
            </span>
            <div>
              Meet Line<small>Your AI booking assistant</small>
            </div>
          </div>
          <ul>
            <li>
              <ProductIcon name="check" /> Talk through what you need.
            </li>
            <li>
              <ProductIcon name="check" /> Choose an available appointment.
            </li>
            <li>
              <ProductIcon name="check" /> Keep your bookings in one place.
            </li>
          </ul>
        </section>
        <section className="auth-card" aria-labelledby="auth-title">
          <span className="auth-card-icon">
            <ProductIcon name={signup ? "home" : "calendar"} />
          </span>
          <h2 id="auth-title">
            {signup ? "Make yourself at home." : "Good to have you back."}
          </h2>
          <p>
            {signup
              ? "Create your account to book with Line."
              : "Sign in to book or view your appointments."}
          </p>
          <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
            {signup && (
              <label htmlFor="full_name">
                Your name
                <input
                  autoComplete="name"
                  id="full_name"
                  name="full_name"
                  required
                  maxLength={160}
                  disabled={busy}
                  placeholder="Full name"
                />
              </label>
            )}
            <label htmlFor="email">
              Email address
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
                required
                disabled={busy}
                placeholder="you@example.com"
              />
            </label>
            <label htmlFor="password">
              Password
              <span className="password-field">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={signup ? "new-password" : "current-password"}
                  minLength={signup ? 15 : 1}
                  maxLength={128}
                  required
                  disabled={busy}
                  aria-describedby={signup ? "password-help" : undefined}
                  placeholder={
                    signup ? "Create a strong password" : "Your password"
                  }
                />
                <button
                  type="button"
                  aria-pressed={showPassword}
                  aria-controls="password"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </span>
            </label>
            {signup && (
              <p className="auth-field-help" id="password-help">
                Use at least 15 characters. A few memorable words work well.
              </p>
            )}
            <div className="early-access-note">
              <strong>Early access</strong>
              <p>
                Please use fictional account and service details. This
                experience is not open for real customer information yet.
              </p>
            </div>
            {signup && (
              <label className="auth-checkbox">
                <input
                  name="fictional_data_acknowledged"
                  type="checkbox"
                  required
                  disabled={busy}
                />
                <span>
                  I’ll use fictional details for this early access experience.
                </span>
              </label>
            )}
            {error && (
              <p className="customer-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="product-button auth-submit"
              disabled={busy}
              type="submit"
            >
              {busy
                ? "Just a moment…"
                : signup
                  ? "Create account & book"
                  : "Sign in & continue"}
              {!busy && <ProductIcon name="arrow" />}
            </button>
          </form>
          <p className="auth-switch">
            {signup ? "Already have an account?" : "New to HVACLine?"}{" "}
            <Link href={signup ? "/login" : "/signup"}>
              {signup ? "Sign in" : "Create an account"}
            </Link>
          </p>
          <p className="auth-privacy">
            <ProductIcon name="shield" /> Your microphone stays off until you
            choose to start.
          </p>
        </section>
      </main>
      <footer className="auth-footer product-container">
        Good service starts with a better conversation.
      </footer>
    </div>
  );
}
