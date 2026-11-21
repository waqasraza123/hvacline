import { Redirect } from "expo-router";
import { useSession } from "../lib/session";
export default function Index() {
  return <Redirect href={useSession().user ? "/(tabs)" : "/sign-in"} />;
}
