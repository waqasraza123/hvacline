import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  type AuthPageProps,
  authPageHref,
  authReturnHref,
  parseAuthIntent,
} from "@/features/customer/auth-continuation";
import { CustomerMfaForm } from "@/features/customer/mfa-form";
import {
  CUSTOMER_MFA_COOKIE,
  currentCustomer,
} from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Required authenticator verification" };

export default async function MfaPage({ searchParams }: AuthPageProps) {
  const intent = parseAuthIntent((await searchParams).intent);
  if ((await currentCustomer()).status === "authenticated")
    redirect(authReturnHref(intent));
  if (!(await cookies()).has(CUSTOMER_MFA_COOKIE))
    redirect(authPageHref("/login", intent));
  return <CustomerMfaForm intent={intent} />;
}
