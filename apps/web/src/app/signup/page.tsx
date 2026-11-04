import { redirect } from "next/navigation";
import {
  type AuthPageProps,
  authReturnHref,
  parseAuthIntent,
} from "@/features/customer/auth-continuation";
import { AuthForm } from "@/features/customer/auth-form";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Create your account" };

export default async function SignupPage({ searchParams }: AuthPageProps) {
  const intent = parseAuthIntent((await searchParams).intent);
  if ((await currentCustomer()).status === "authenticated")
    redirect(authReturnHref(intent));
  return <AuthForm mode="signup" intent={intent} />;
}
