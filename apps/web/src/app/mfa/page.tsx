import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { CustomerMfaForm } from "@/features/customer/mfa-form";
import { CUSTOMER_MFA_COOKIE, currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Required authenticator verification" };

export default async function MfaPage() {
  if ((await currentCustomer()).status === "authenticated") redirect("/book");
  if (!(await cookies()).has(CUSTOMER_MFA_COOKIE)) redirect("/login");
  return <CustomerMfaForm />;
}
