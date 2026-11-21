"use client";

import type { Dispatch, SetStateAction } from "react";
import { websiteAssets } from "./assets";
import { fontIds } from "./contracts";
import type {
  ContentItem,
  SectionId,
  WebsiteAction,
  WebsiteConfiguration,
} from "./contracts";
import { websiteTemplates } from "./templates";
import styles from "./website-manager.module.css";

type Props = {
  configuration: WebsiteConfiguration;
  setConfiguration: Dispatch<SetStateAction<WebsiteConfiguration>>;
};

function TextField({
  label,
  value,
  onChange,
  max = 800,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  max?: number;
  multiline?: boolean;
}) {
  const props = {
    value,
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => onChange(event.target.value),
    required: true,
    maxLength: max,
  };
  return (
    <label>
      {label}
      {multiline ? <textarea {...props} /> : <input {...props} />}
    </label>
  );
}

function AssetSelect({
  label,
  value,
  onChange,
  logo = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  logo?: boolean;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {Object.entries(websiteAssets)
          .filter(([, asset]) => (logo ? asset.width <= 48 : asset.width > 48))
          .map(([id, asset]) => (
            <option key={id} value={id}>
              {asset.alt}
            </option>
          ))}
      </select>
    </label>
  );
}

function ContentList({
  label,
  items,
  onChange,
  maximum,
}: {
  label: string;
  items: readonly ContentItem[];
  onChange: (items: ContentItem[]) => void;
  maximum: number;
}) {
  return (
    <div>
      <h3>{label}</h3>
      {items.map((item, index) => (
        <div className={styles.service} key={index}>
          <TextField
            label={`${label} ${index + 1} title`}
            value={item.title}
            max={140}
            onChange={(title) =>
              onChange(
                items.map((row, at) =>
                  at === index ? { ...row, title } : row,
                ),
              )
            }
          />
          <TextField
            label={`${label} ${index + 1} description`}
            value={item.description}
            multiline
            onChange={(description) =>
              onChange(
                items.map((row, at) =>
                  at === index ? { ...row, description } : row,
                ),
              )
            }
          />
          <button
            type="button"
            disabled={items.length <= 1}
            onClick={() => onChange(items.filter((_, at) => at !== index))}
          >
            Remove {label.toLowerCase()} {index + 1}
          </button>
        </div>
      ))}
      <button
        type="button"
        disabled={items.length >= maximum}
        onClick={() =>
          onChange([
            ...items,
            { title: "New item", description: "Describe this item." },
          ])
        }
      >
        Add {label.toLowerCase()}
      </button>
    </div>
  );
}

function ActionEditor({
  label,
  action,
  sections,
  onChange,
}: {
  label: string;
  action: WebsiteAction;
  sections: readonly SectionId[];
  onChange: (action: WebsiteAction) => void;
}) {
  return (
    <div className={styles.service}>
      <TextField
        label={`${label} CTA label`}
        value={action.label}
        max={70}
        onChange={(text) => onChange({ ...action, label: text })}
      />
      <label>
        {label} CTA destination
        <select
          value={action.destination.kind}
          onChange={(event) =>
            onChange({
              ...action,
              destination:
                event.target.value === "url"
                  ? { kind: "url", href: "/" }
                  : event.target.value === "section"
                    ? { kind: "section", section: "contact" }
                    : { kind: "voice" },
            })
          }
        >
          <option value="voice">This website’s receptionist</option>
          <option value="section">Page section</option>
          <option value="url">Approved URL</option>
        </select>
      </label>
      {action.destination.kind === "section" && (
        <label>
          Target section
          <select
            value={action.destination.section}
            onChange={(event) =>
              onChange({
                ...action,
                destination: {
                  kind: "section",
                  section: event.target.value as SectionId,
                },
              })
            }
          >
            {sections.map((section) => (
              <option key={section}>{section}</option>
            ))}
          </select>
        </label>
      )}
      {action.destination.kind === "url" && (
        <TextField
          label="Destination URL (local path or HTTPS)"
          value={action.destination.href}
          max={500}
          onChange={(href) =>
            onChange({ ...action, destination: { kind: "url", href } })
          }
        />
      )}
    </div>
  );
}

export function WebsiteContentEditor({
  configuration: c,
  setConfiguration: set,
}: Props) {
  function sections(next: readonly SectionId[]) {
    set((current) => ({
      ...current,
      sections: next,
      header: {
        navigation: current.header.navigation.some((link) => next.includes(link.section))
          ? current.header.navigation.filter((link) => next.includes(link.section))
          : [{ label: "Contact", section: "contact" }],
      },
      actions: Object.fromEntries(
        Object.entries(current.actions).map(([key, action]) => [
          key,
          action.destination.kind === "section" &&
          !next.includes(action.destination.section)
            ? { ...action, destination: { kind: "voice" } }
            : action,
        ]),
      ) as WebsiteConfiguration["actions"],
    }));
  }
  const template = websiteTemplates[c.templateId];
  return (
    <>
      <details open className={styles.editorSection}>
        <summary>Branding & appearance</summary>
        <TextField
          label="Business name"
          value={c.brand.name}
          max={70}
          onChange={(name) => set({ ...c, brand: { ...c.brand, name } })}
        />
        <TextField
          label="Brand tagline"
          value={c.brand.tagline}
          max={100}
          onChange={(tagline) => set({ ...c, brand: { ...c.brand, tagline } })}
        />
        <div className={styles.grid}>
          <AssetSelect
            label="Logo"
            value={c.brand.logo}
            logo
            onChange={(logo) => set({ ...c, brand: { ...c.brand, logo } })}
          />
          <AssetSelect
            label="Favicon"
            value={c.brand.favicon}
            logo
            onChange={(favicon) =>
              set({ ...c, brand: { ...c.brand, favicon } })
            }
          />
        </div>
        <p className="section-help">
          Choose from approved artwork. Remote URLs and uploads are not
          accepted.
        </p>
        <div className={styles.grid}>
          {(["headingFont", "bodyFont"] as const).map((key) => (
            <label key={key}>
              {key === "headingFont" ? "Heading typography" : "Body typography"}
              <select
                value={c.appearance[key]}
                onChange={(event) =>
                  set({
                    ...c,
                    appearance: { ...c.appearance, [key]: event.target.value },
                  })
                }
              >
                {fontIds.map((font) => (
                  <option key={font}>{font}</option>
                ))}
              </select>
            </label>
          ))}
          <label>
            Spacing
            <select
              value={c.appearance.spacing}
              onChange={(event) =>
                set({
                  ...c,
                  appearance: {
                    ...c.appearance,
                    spacing: event.target
                      .value as WebsiteConfiguration["appearance"]["spacing"],
                  },
                })
              }
            >
              {["compact", "balanced", "airy"].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
        </div>
        {(["light", "dark"] as const).map((mode) => (
          <div key={mode}>
            <h3>{mode === "light" ? "Light" : "Dark"} theme colors</h3>
            <div className={styles.colors}>
              {Object.entries(c.appearance[mode]).map(([key, value]) => (
                <label key={key}>
                  {key}
                  <input
                    type="color"
                    value={value}
                    onChange={(event) =>
                      set({
                        ...c,
                        appearance: {
                          ...c.appearance,
                          [mode]: {
                            ...c.appearance[mode],
                            [key]: event.target.value,
                          },
                        },
                      })
                    }
                  />
                </label>
              ))}
            </div>
          </div>
        ))}
      </details>
      <details open className={styles.editorSection}>
        <summary>Hero & calls to action</summary>
        <TextField
          label="Hero eyebrow"
          value={c.hero.eyebrow}
          max={90}
          onChange={(eyebrow) => set({ ...c, hero: { ...c.hero, eyebrow } })}
        />
        <TextField
          label="Headline"
          value={c.hero.title}
          max={160}
          onChange={(title) => set({ ...c, hero: { ...c.hero, title } })}
        />
        <TextField
          label="Hero description"
          value={c.hero.description}
          multiline
          onChange={(description) =>
            set({ ...c, hero: { ...c.hero, description } })
          }
        />
        <AssetSelect
          label="Hero artwork"
          value={c.hero.image}
          onChange={(image) => set({ ...c, hero: { ...c.hero, image } })}
        />
        <TextField
          label="Hero image caption"
          value={c.hero.imageCaption}
          max={180}
          onChange={(imageCaption) =>
            set({ ...c, hero: { ...c.hero, imageCaption } })
          }
        />
        {(["primary", "secondary"] as const).map((key) => (
          <ActionEditor
            key={key}
            label={key === "primary" ? "Primary" : "Secondary"}
            action={c.actions[key]}
            sections={c.sections}
            onChange={(action) =>
              set({ ...c, actions: { ...c.actions, [key]: action } })
            }
          />
        ))}
      </details>
      <details className={styles.editorSection}>
        <summary>Sections & navigation</summary>
        <ol className={styles.sectionList}>
          {c.sections.map((section, index) => (
            <li key={section}>
              <span>
                {section}
                {template.requiredSections.includes(section)
                  ? " · required"
                  : ""}
              </span>
              <button
                type="button"
                aria-label={`Move ${section} up`}
                disabled={index === 0}
                onClick={() => {
                  const next = [...c.sections];
                  [next[index - 1], next[index]] = [
                    next[index],
                    next[index - 1],
                  ];
                  sections(next);
                }}
              >
                ↑
              </button>
              <button
                type="button"
                aria-label={`Move ${section} down`}
                disabled={index === c.sections.length - 1}
                onClick={() => {
                  const next = [...c.sections];
                  [next[index + 1], next[index]] = [
                    next[index],
                    next[index + 1],
                  ];
                  sections(next);
                }}
              >
                ↓
              </button>
              <button
                type="button"
                disabled={template.requiredSections.includes(section)}
                onClick={() =>
                  sections(c.sections.filter((value) => value !== section))
                }
              >
                Remove {section}
              </button>
            </li>
          ))}
        </ol>
        {template.supportedSections
          .filter((section) => !c.sections.includes(section))
          .map((section) => (
            <button
              type="button"
              key={section}
              onClick={() => sections([...c.sections, section])}
            >
              Add {section}
            </button>
          ))}
        <h3>Header links</h3>
        {c.header.navigation.map((link, index) => (
          <div key={index} className={styles.service}>
            <TextField
              label={`Navigation ${index + 1} label`}
              value={link.label}
              max={40}
              onChange={(label) =>
                set({
                  ...c,
                  header: {
                    navigation: c.header.navigation.map((row, at) =>
                      at === index ? { ...row, label } : row,
                    ),
                  },
                })
              }
            />
            <label>
              Navigation section
              <select
                value={link.section}
                onChange={(event) =>
                  set({
                    ...c,
                    header: {
                      navigation: c.header.navigation.map((row, at) =>
                        at === index
                          ? { ...row, section: event.target.value as SectionId }
                          : row,
                      ),
                    },
                  })
                }
              >
                {c.sections.map((section) => (
                  <option key={section}>{section}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={c.header.navigation.length <= 1}
              onClick={() =>
                set({
                  ...c,
                  header: {
                    navigation: c.header.navigation.filter(
                      (_, at) => at !== index,
                    ),
                  },
                })
              }
            >
              Remove link {index + 1}
            </button>
          </div>
        ))}
        <button
          type="button"
          disabled={c.header.navigation.length >= 5}
          onClick={() =>
            set({
              ...c,
              header: {
                navigation: [
                  ...c.header.navigation,
                  { label: "Contact", section: "contact" },
                ],
              },
            })
          }
        >
          Add header link
        </button>
      </details>
      <details className={styles.editorSection}>
        <summary>Services & page content</summary>
        <ContentList
          label="Services"
          items={c.services}
          maximum={6}
          onChange={(services) => set({ ...c, services })}
        />
        {c.sections.includes("process") && (
          <ContentList
            label="Process steps"
            items={c.process}
            maximum={5}
            onChange={(process) => set({ ...c, process })}
          />
        )}
        {c.sections.includes("showcase") && (
          <>
            <h3>Property showcase</h3>
            {c.showcase.map((item, index) => (
              <div key={index} className={styles.service}>
                <TextField
                  label={`Property ${index + 1} title`}
                  value={item.title}
                  max={140}
                  onChange={(title) =>
                    set({
                      ...c,
                      showcase: c.showcase.map((row, at) =>
                        at === index ? { ...row, title } : row,
                      ),
                    })
                  }
                />
                <TextField
                  label={`Property ${index + 1} description`}
                  value={item.description}
                  multiline
                  onChange={(description) =>
                    set({
                      ...c,
                      showcase: c.showcase.map((row, at) =>
                        at === index ? { ...row, description } : row,
                      ),
                    })
                  }
                />
                <TextField
                  label={`Property ${index + 1} label`}
                  value={item.label}
                  max={80}
                  onChange={(label) =>
                    set({
                      ...c,
                      showcase: c.showcase.map((row, at) =>
                        at === index ? { ...row, label } : row,
                      ),
                    })
                  }
                />
                <AssetSelect
                  label={`Property ${index + 1} artwork`}
                  value={item.image}
                  onChange={(image) =>
                    set({
                      ...c,
                      showcase: c.showcase.map((row, at) =>
                        at === index ? { ...row, image } : row,
                      ),
                    })
                  }
                />
                <button
                  type="button"
                  disabled={c.showcase.length <= 1}
                  onClick={() =>
                    set({
                      ...c,
                      showcase: c.showcase.filter((_, at) => at !== index),
                    })
                  }
                >
                  Remove property {index + 1}
                </button>
              </div>
            ))}
            <button
              type="button"
              disabled={c.showcase.length >= 4}
              onClick={() =>
                set({
                  ...c,
                  showcase: [
                    ...c.showcase,
                    {
                      title: "Property",
                      description: "Approved property details.",
                      label: "Inquiry",
                      image: "courtyard-home",
                    },
                  ],
                })
              }
            >
              Add property
            </button>
          </>
        )}
        {c.sections.includes("story") && (
          <>
            <TextField
              label="Story eyebrow"
              value={c.story.eyebrow}
              max={90}
              onChange={(eyebrow) =>
                set({ ...c, story: { ...c.story, eyebrow } })
              }
            />
            <TextField
              label="Story title"
              value={c.story.title}
              max={140}
              onChange={(title) => set({ ...c, story: { ...c.story, title } })}
            />
            <TextField
              label="Story description"
              value={c.story.description}
              multiline
              onChange={(description) =>
                set({ ...c, story: { ...c.story, description } })
              }
            />
            <AssetSelect
              label="Story artwork"
              value={c.story.image}
              onChange={(image) => set({ ...c, story: { ...c.story, image } })}
            />
          </>
        )}
        <TextField
          label="Receptionist section title"
          value={c.voice.title}
          max={140}
          onChange={(title) => set({ ...c, voice: { ...c.voice, title } })}
        />
        <TextField
          label="Receptionist section description"
          value={c.voice.description}
          multiline
          onChange={(description) =>
            set({ ...c, voice: { ...c.voice, description } })
          }
        />
        <p className="section-help">
          Written examples are illustrative, not recorded conversations or agent
          instructions.
        </p>
        {c.voice.examples.map((example, index) => (
          <div key={index}>
            <label>
              Example {index + 1} speaker
              <select
                value={example.role}
                onChange={(event) =>
                  set({
                    ...c,
                    voice: {
                      ...c.voice,
                      examples: c.voice.examples.map((row, at) =>
                        at === index
                          ? {
                              ...row,
                              role: event.target.value as
                                "visitor" | "assistant",
                            }
                          : row,
                      ),
                    },
                  })
                }
              >
                <option value="visitor">Visitor</option>
                <option value="assistant">Assistant</option>
              </select>
            </label>
            <TextField
              label={`Example ${index + 1} text`}
              value={example.text}
              max={500}
              onChange={(text) =>
                set({
                  ...c,
                  voice: {
                    ...c.voice,
                    examples: c.voice.examples.map((row, at) =>
                      at === index ? { ...row, text } : row,
                    ),
                  },
                })
              }
            />
          </div>
        ))}
        <h3>FAQs</h3>
        {c.faqs.map((faq, index) => (
          <div className={styles.service} key={index}>
            <TextField
              label={`FAQ ${index + 1} question`}
              value={faq.question}
              max={180}
              onChange={(question) =>
                set({
                  ...c,
                  faqs: c.faqs.map((row, at) =>
                    at === index ? { ...row, question } : row,
                  ),
                })
              }
            />
            <TextField
              label={`FAQ ${index + 1} answer`}
              value={faq.answer}
              multiline
              onChange={(answer) =>
                set({
                  ...c,
                  faqs: c.faqs.map((row, at) =>
                    at === index ? { ...row, answer } : row,
                  ),
                })
              }
            />
            <button
              type="button"
              disabled={c.faqs.length <= 1}
              onClick={() =>
                set({ ...c, faqs: c.faqs.filter((_, at) => at !== index) })
              }
            >
              Remove FAQ {index + 1}
            </button>
          </div>
        ))}
        <button
          type="button"
          disabled={c.faqs.length >= 8}
          onClick={() =>
            set({
              ...c,
              faqs: [
                ...c.faqs,
                { question: "New question", answer: "Approved answer." },
              ],
            })
          }
        >
          Add FAQ
        </button>
      </details>
      <details className={styles.editorSection}>
        <summary>Contact & SEO</summary>
        {(["title", "description", "location", "hours"] as const).map((key) => (
          <TextField
            key={key}
            label={`Contact ${key}`}
            value={c.contact[key]}
            max={key === "title" ? 140 : key === "description" ? 800 : 160}
            onChange={(value) =>
              set({ ...c, contact: { ...c.contact, [key]: value } })
            }
          />
        ))}
        <label>
          Contact email
          <input
            type="email"
            maxLength={254}
            value={c.contact.email ?? ""}
            onChange={(event) =>
              set({
                ...c,
                contact: { ...c.contact, email: event.target.value || null },
              })
            }
          />
        </label>
        <label>
          Contact phone (E.164)
          <input
            maxLength={16}
            pattern="\+[1-9][0-9]{7,14}"
            value={c.contact.phone ?? ""}
            onChange={(event) =>
              set({
                ...c,
                contact: { ...c.contact, phone: event.target.value || null },
              })
            }
          />
        </label>
        <TextField
          label="SEO title"
          value={c.seo.title}
          max={120}
          onChange={(title) => set({ ...c, seo: { ...c.seo, title } })}
        />
        <TextField
          label="SEO description"
          value={c.seo.description}
          max={240}
          multiline
          onChange={(description) =>
            set({ ...c, seo: { ...c.seo, description } })
          }
        />
        <TextField
          label="Industry"
          value={c.industry}
          max={60}
          onChange={(industry) => set({ ...c, industry })}
        />
        <TextField
          label="Design style description"
          value={c.designStyle}
          max={60}
          onChange={(designStyle) => set({ ...c, designStyle })}
        />
        <TextField
          label="Website summary"
          value={c.summary}
          max={220}
          multiline
          onChange={(summary) => set({ ...c, summary })}
        />
      </details>
    </>
  );
}
