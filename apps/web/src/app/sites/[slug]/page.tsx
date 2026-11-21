import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { publishedWebsite } from "@/features/websites/published.server";
import { WebsiteRenderer } from "@/features/websites/renderer";
import { websiteAsset } from "@/features/websites/assets";

export const dynamic = "force-dynamic";
type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const site = await publishedWebsite((await params).slug);
  if (!site) notFound();
  return {
    title: { absolute: site.configuration.seo.title },
    description: site.configuration.seo.description,
    icons: { icon: websiteAsset(site.configuration.brand.favicon).src },
    openGraph: {
      title: site.configuration.seo.title,
      description: site.configuration.seo.description,
    },
    robots: { index: false, follow: false },
  };
}

export default async function PublishedWebsite({ params }: Props) {
  const site = await publishedWebsite((await params).slug);
  if (!site) notFound();
  return <WebsiteRenderer site={site} />;
}
