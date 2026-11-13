import Link from "next/link";
import styles from "@/features/websites/website.module.css";

export default function SiteNotFound() {
  return (
    <main className={styles.utility}>
      <h1>This website is not available.</h1>
      <p>It may be unpublished or disabled.</p>
      <Link href="/">Back to HVACLine home</Link>
    </main>
  );
}
