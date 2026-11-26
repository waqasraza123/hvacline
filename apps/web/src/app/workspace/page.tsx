import { WorkspacePortal } from "@/features/workspace/portal";
import "../product.css";

export const metadata = { title: "Staff workspace", robots: { index: false, follow: false } };
export default function WorkspacePage() { return <WorkspacePortal />; }
