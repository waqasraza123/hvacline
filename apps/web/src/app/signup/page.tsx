import { redirect } from "next/navigation";
import { AuthForm } from "@/features/customer/auth-form";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Create your account" };

export default async function SignupPage() {
  if ((await currentCustomer()).status === "authenticated") redirect("/book");
  return <AuthForm mode="signup" />;
}
