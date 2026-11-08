import Link from "next/link";
import { currentCustomer } from "@/features/customer/server";
import { AccountAvatar } from "./account-avatar";

export async function HeaderAccount() {
  const customer = await currentCustomer();
  if (customer.status === "authenticated")
    return <AccountAvatar fullName={customer.user.full_name} />;
  return (
    <Link
      className="product-login"
      href={customer.status === "anonymous" ? "/login" : "/book"}
    >
      {customer.status === "anonymous" ? "Sign in" : "My account"}
    </Link>
  );
}
