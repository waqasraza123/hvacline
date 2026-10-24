import { redirect } from "next/navigation";
import { AuthForm } from "@/features/customer/auth-form";
import { currentCustomer } from "@/features/customer/server";
import "../product.css";

export const metadata = { title: "Sign in" };

export default async function LoginPage() {
  if ((await currentCustomer()).status === "authenticated") redirect("/book");
  return <AuthForm mode="login" />;
}
