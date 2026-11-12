export const websiteAssets = {
  "hvac-mark": { src: "/icon.svg", alt: "HVACLine", width: 36, height: 36 },
  "estate-mark": { src: "/demo-assets/estate-mark.svg", alt: "Alder & Stone", width: 48, height: 48 },
  "calm-mark": { src: "/demo-assets/calm-mark.svg", alt: "Morrow Studio", width: 48, height: 48 },
  "hvac-equipment": { src: "/demo-assets/hvac-equipment.svg", alt: "Architectural illustration of a home and outdoor HVAC equipment", width: 1200, height: 1000 },
  "courtyard-home": { src: "/demo-assets/courtyard-home.svg", alt: "Illustrated modern courtyard home in warm stone with olive trees", width: 1400, height: 1000 },
  "city-residence": { src: "/demo-assets/city-residence.svg", alt: "Illustrated brick residence with tall windows and landscaped entry", width: 1000, height: 1200 },
  "calm-studio": { src: "/demo-assets/calm-studio.svg", alt: "Sunlit illustrated studio with a sage chair, plant and appointment notebook", width: 1200, height: 1100 },
} as const;

export function websiteAsset(id: string) {
  if (!Object.prototype.hasOwnProperty.call(websiteAssets, id)) {
    throw new Error(`Website asset is not approved: ${id}`);
  }
  return websiteAssets[id as keyof typeof websiteAssets];
}
