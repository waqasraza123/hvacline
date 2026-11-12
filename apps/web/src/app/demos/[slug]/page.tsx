import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { websiteAsset } from "@/features/websites/assets";
import { demoWebsites } from "@/features/websites/catalog";
import { resolveDemoWebsite } from "@/features/websites/registry.server";
import { WebsiteRenderer } from "@/features/websites/renderer";

type DemoPageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return demoWebsites.map((website) => ({ slug: website.slug }));
}

export async function generateMetadata({
  params,
}: DemoPageProps): Promise<Metadata> {
  const { slug } = await params;
  const site = await resolveDemoWebsite(slug);
  if (!site) notFound();
  const configuration = site.configuration;
  return {
    title: { absolute: configuration.seo.title },
    description: configuration.seo.description,
    robots: { index: false, follow: false },
    icons: {
      icon: websiteAsset(configuration.brand.favicon).src,
      shortcut: websiteAsset(configuration.brand.favicon).src,
    },
    openGraph: {
      title: configuration.seo.title,
      description: configuration.seo.description,
      type: "website",
    },
  };
}

export default async function DemoWebsitePage({ params }: DemoPageProps) {
  const { slug } = await params;
  const site = await resolveDemoWebsite(
    slug,
    process.env.NEXT_PUBLIC_CONVERSATION_AI_ENABLED === "true",
  );
  if (!site) notFound();
  return <WebsiteRenderer site={site} />;
}
