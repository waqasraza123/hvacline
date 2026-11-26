import { WorkspaceBootstrap } from "@/features/workspace/bootstrap";
import "../../product.css";

export const metadata = { title: "Business setup", robots: { index: false, follow: false } };
export default function WorkspaceSetupPage() { return <WorkspaceBootstrap />; }
