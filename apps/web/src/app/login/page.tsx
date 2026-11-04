import { redirect } from "next/navigation";
import {
  type AuthPageProps,
  authReturnHref,
  parseAuthIntent,
} from "@/features/customer/auth-continuation";
import { AuthForm } from "@/features/customer/auth-form";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: AuthPageProps) {
  const intent = parseAuthIntent((await searchParams).intent);
  if ((await currentCustomer()).status === "authenticated")
    redirect(authReturnHref(intent));
  return <AuthForm mode="login" intent={intent} />;
}
