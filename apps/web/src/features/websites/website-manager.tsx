"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { requestApi } from "@/features/operations/api";
import { websiteAssets } from "./assets";
import { newWebsiteConfiguration } from "./editor";
import type { TemplateId, WebsiteConfiguration } from "./contracts";
import { WebsiteRenderer } from "./renderer";
import { websiteTemplates } from "./templates";
import {
  validateTemplateCompatibility,
  validateWebsiteConfiguration,
} from "./validation";
import styles from "./website-manager.module.css";

type WebsiteRecord = {
  id: string;
  slug: string;
  configuration: WebsiteConfiguration;
  status: "draft" | "published" | "disabled";
  row_version: number;
  agent_binding_id: string | null;
  knowledge_faq_ids: string[];
  voice_enabled: boolean;
  lead_capture_enabled: boolean;
};
type Management = {
  websites: WebsiteRecord[];
  agents: { id: string; label: string; enabled: boolean }[];
  knowledge: { id: string; question: string }[];
};

export function WebsiteManager({
  apiBaseUrl,
  token,
}: {
  apiBaseUrl: string;
  token: string;
}) {
  const [management, setManagement] = useState<Management>();
  const [record, setRecord] = useState<WebsiteRecord>();
  const [configuration, setConfiguration] = useState<WebsiteConfiguration>(() =>
    newWebsiteConfiguration("industrial"),
  );
  const [status, setStatus] = useState<WebsiteRecord["status"]>("draft");
  const [agent, setAgent] = useState("");
  const [knowledge, setKnowledge] = useState<string[]>([]);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [leadCapture, setLeadCapture] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    void requestApi<Management>(apiBaseUrl, token, "websites")
      .then((data) => {
        if (active) setManagement(data);
      })
      .catch((failure: unknown) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "Websites could not be loaded.",
          );
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, token, reload]);

  function choose(next?: WebsiteRecord) {
    setRecord(next);
    setConfiguration(
      next
        ? validateWebsiteConfiguration(next.configuration)
        : newWebsiteConfiguration("industrial"),
    );
    setStatus(next?.status ?? "draft");
    setAgent(next?.agent_binding_id ?? "");
    setKnowledge(next?.knowledge_faq_ids ?? []);
    setVoiceEnabled(next?.voice_enabled ?? false);
    setLeadCapture(next?.lead_capture_enabled ?? false);
    setMessage("");
    setError("");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const parsed = validateWebsiteConfiguration({
        ...configuration,
        agentConfigurationRef: "server-managed",
      });
      validateTemplateCompatibility(
        parsed,
        websiteTemplates[parsed.templateId],
      );
      const next = await requestApi<WebsiteRecord>(
        apiBaseUrl,
        token,
        record ? `websites/${record.id}` : "websites",
        record ? "PUT" : "POST",
        {
          expected_row_version: record?.row_version ?? 0,
          configuration: parsed,
          status,
          agent_binding_id: agent || null,
          knowledge_faq_ids: knowledge,
          voice_enabled: voiceEnabled,
          lead_capture_enabled: leadCapture,
        },
      );
      setRecord(next);
      setConfiguration(validateWebsiteConfiguration(next.configuration));
      setMessage(
        "Website saved. Voice availability still depends on its configured agent and backend settings.",
      );
      setReload((value) => value + 1);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "The website could not be saved. Reload its latest version before retrying a conflict.",
      );
    } finally {
      setBusy(false);
    }
  }

  const assets = Object.entries(websiteAssets);
  return (
    <section className="ops-card">
      <h2>Your websites</h2>
      <p className="section-help">
        Business-owned configuration under the existing administrator gate.
        Published websites use /sites/slug; static demos remain separate.
        Provider IDs and credentials are managed on the server.
      </p>
      <div className={styles.selection}>
        <label>
          Website
          <select
            disabled={busy}
            value={record?.id ?? ""}
            onChange={(event) =>
              choose(
                management?.websites.find(
                  (site) => site.id === event.target.value,
                ),
              )
            }
          >
            <option value="">Create a website</option>
            {management?.websites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.configuration.brand.name} · {site.status}
              </option>
            ))}
          </select>
        </label>
        {record && (
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              void requestApi<Management>(apiBaseUrl, token, "websites")
                .then((data) => {
                  setManagement(data);
                  choose(data.websites.find((site) => site.id === record.id));
                })
                .catch((failure: unknown) =>
                  setError(
                    failure instanceof Error
                      ? failure.message
                      : "Unable to reload.",
                  ),
                );
            }}
          >
            Reload saved version
          </button>
        )}
      </div>
      {error && (
        <div role="alert" className="ops-error">
          {error}
          {!management && (
            <button
              type="button"
              onClick={() => {
                setError("");
                setReload((value) => value + 1);
              }}
            >
              Retry loading websites
            </button>
          )}
        </div>
      )}
      {!management && !error && (
        <p role="status">Loading your websites and authorized agents…</p>
      )}
      {management?.websites.length === 0 && (
        <p className="section-help">
          No websites yet. Choose a template, review its content and save your
          first draft.
        </p>
      )}
      {message && (
        <p role="status" className="ops-message">
          {message}
        </p>
      )}
      <form onSubmit={(event) => void save(event)}>
        <fieldset disabled={busy || !management} className={styles.fields}>
          <div className={styles.grid}>
            <label>
              Website slug
              <input
                required
                pattern="[a-z0-9]+(-[a-z0-9]+)*"
                maxLength={64}
                disabled={!!record}
                value={configuration.slug}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    slug: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Website name
              <input
                required
                maxLength={70}
                value={configuration.brand.name}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    brand: { ...configuration.brand, name: event.target.value },
                  })
                }
              />
            </label>
            <label>
              Template
              <select
                value={configuration.templateId}
                onChange={(event) => {
                  setConfiguration(
                    newWebsiteConfiguration(
                      event.target.value as TemplateId,
                      configuration.slug,
                      configuration.brand.name,
                    ),
                  );
                }}
              >
                <option value="industrial">Industrial HVAC</option>
                <option value="editorial">Editorial real estate</option>
                <option value="calm">Calm appointments</option>
              </select>
              <small>
                Changing template resets its content/layout defaults.
              </small>
            </label>
            <label>
              Visibility
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as WebsiteRecord["status"])
                }
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="disabled">Disabled</option>
              </select>
            </label>
            <label>
              Logo
              <select
                value={configuration.brand.logo}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    brand: {
                      ...configuration.brand,
                      logo: event.target.value,
                      favicon: event.target.value,
                    },
                  })
                }
              >
                {assets
                  .filter(([, asset]) => asset.width <= 48)
                  .map(([id]) => (
                    <option key={id}>{id}</option>
                  ))}
              </select>
            </label>
            <label>
              Hero artwork
              <select
                value={configuration.hero.image}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    hero: { ...configuration.hero, image: event.target.value },
                  })
                }
              >
                {assets
                  .filter(([, asset]) => asset.width > 48)
                  .map(([id]) => (
                    <option key={id}>{id}</option>
                  ))}
              </select>
            </label>
            <label>
              Primary color
              <input
                type="color"
                value={configuration.appearance.light.accent}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    appearance: {
                      ...configuration.appearance,
                      light: {
                        ...configuration.appearance.light,
                        accent: event.target.value,
                      },
                    },
                  })
                }
              />
            </label>
            <label>
              Secondary surface color
              <input
                type="color"
                value={configuration.appearance.light.surface}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    appearance: {
                      ...configuration.appearance,
                      light: {
                        ...configuration.appearance.light,
                        surface: event.target.value,
                      },
                    },
                  })
                }
              />
            </label>
          </div>
          <label>
            Headline
            <input
              required
              maxLength={160}
              value={configuration.hero.title}
              onChange={(event) =>
                setConfiguration({
                  ...configuration,
                  hero: { ...configuration.hero, title: event.target.value },
                })
              }
            />
          </label>
          <label>
            Description
            <textarea
              required
              maxLength={800}
              value={configuration.hero.description}
              onChange={(event) =>
                setConfiguration({
                  ...configuration,
                  hero: {
                    ...configuration.hero,
                    description: event.target.value,
                  },
                })
              }
            />
          </label>
          <div className={styles.grid}>
            {(["primary", "secondary"] as const).map((key) => (
              <label key={key}>
                {key === "primary" ? "Primary" : "Secondary"} CTA label
                <input
                  required
                  maxLength={70}
                  value={configuration.actions[key].label}
                  onChange={(event) =>
                    setConfiguration({
                      ...configuration,
                      actions: {
                        ...configuration.actions,
                        [key]: {
                          ...configuration.actions[key],
                          label: event.target.value,
                        },
                      },
                    })
                  }
                />
              </label>
            ))}
          </div>
          <h3>Services & features</h3>
          {configuration.services.map((service, index) => (
            <div className={styles.service} key={index}>
              <label>
                Title
                <input
                  required
                  maxLength={140}
                  value={service.title}
                  onChange={(event) =>
                    setConfiguration({
                      ...configuration,
                      services: configuration.services.map((row, at) =>
                        at === index
                          ? { ...row, title: event.target.value }
                          : row,
                      ),
                    })
                  }
                />
              </label>
              <label>
                Description
                <textarea
                  required
                  maxLength={800}
                  value={service.description}
                  onChange={(event) =>
                    setConfiguration({
                      ...configuration,
                      services: configuration.services.map((row, at) =>
                        at === index
                          ? { ...row, description: event.target.value }
                          : row,
                      ),
                    })
                  }
                />
              </label>
              <button
                type="button"
                disabled={configuration.services.length <= 1}
                onClick={() =>
                  setConfiguration({
                    ...configuration,
                    services: configuration.services.filter(
                      (_, at) => at !== index,
                    ),
                  })
                }
              >
                Remove service
              </button>
            </div>
          ))}
          <button
            type="button"
            disabled={configuration.services.length >= 6}
            onClick={() =>
              setConfiguration({
                ...configuration,
                services: [
                  ...configuration.services,
                  {
                    title: "New service",
                    description: "Describe this service.",
                  },
                ],
              })
            }
          >
            Add service
          </button>
          <h3>Contact information</h3>
          <div className={styles.grid}>
            <label>
              Location
              <input
                required
                value={configuration.contact.location}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    contact: {
                      ...configuration.contact,
                      location: event.target.value,
                    },
                  })
                }
              />
            </label>
            <label>
              Hours
              <input
                required
                value={configuration.contact.hours}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    contact: {
                      ...configuration.contact,
                      hours: event.target.value,
                    },
                  })
                }
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={configuration.contact.email ?? ""}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    contact: {
                      ...configuration.contact,
                      email: event.target.value || null,
                    },
                  })
                }
              />
            </label>
            <label>
              Phone (E.164)
              <input
                value={configuration.contact.phone ?? ""}
                onChange={(event) =>
                  setConfiguration({
                    ...configuration,
                    contact: {
                      ...configuration.contact,
                      phone: event.target.value || null,
                    },
                  })
                }
              />
            </label>
          </div>
          <h3>Search metadata</h3>
          <label>
            Page title
            <input
              required
              maxLength={120}
              value={configuration.seo.title}
              onChange={(event) =>
                setConfiguration({
                  ...configuration,
                  seo: { ...configuration.seo, title: event.target.value },
                })
              }
            />
          </label>
          <label>
            Page description
            <textarea
              required
              maxLength={240}
              value={configuration.seo.description}
              onChange={(event) =>
                setConfiguration({
                  ...configuration,
                  seo: {
                    ...configuration.seo,
                    description: event.target.value,
                  },
                })
              }
            />
          </label>
          <h3>Agent & capabilities</h3>
          <label>
            Authorized configured agent
            <select
              value={agent}
              onChange={(event) => setAgent(event.target.value)}
            >
              <option value="">No configured agent</option>
              {management?.agents.map((binding) => (
                <option key={binding.id} value={binding.id}>
                  {binding.label}
                  {binding.enabled ? "" : " · unavailable"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={voiceEnabled}
              onChange={(event) => setVoiceEnabled(event.target.checked)}
            />
            Enable Voice and Text for this website
          </label>
          <label>
            <input
              type="checkbox"
              checked={leadCapture}
              onChange={(event) => setLeadCapture(event.target.checked)}
            />
            Allow explicitly confirmed inquiries for human follow-up
          </label>
          <p className="section-help">
            Website booking and persistent memory remain disabled. Separate
            hosted agents must be configured before Voice is available. Only
            approved local artwork is selectable; uploads are a later phase.
          </p>
          <label>
            Approved business knowledge
            <select
              multiple
              size={Math.min(6, Math.max(2, management?.knowledge.length ?? 0))}
              value={knowledge}
              onChange={(event) =>
                setKnowledge(
                  Array.from(
                    event.target.selectedOptions,
                    (option) => option.value,
                  ),
                )
              }
            >
              {management?.knowledge.map((faq) => (
                <option key={faq.id} value={faq.id}>
                  {faq.question}
                </option>
              ))}
            </select>
          </label>
          <small>
            Select only the approved answers this website’s assistant may
            retrieve. An empty selection exposes no knowledge records.
          </small>
          <div className={styles.actions}>
            <button className="primary-link" type="submit">
              {busy ? "Saving…" : "Save website"}
            </button>
            <Dialog.Root open={preview} onOpenChange={setPreview}>
              <Dialog.Trigger asChild>
                <button type="button">Preview website</button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className={styles.overlay} />
                <Dialog.Content className={styles.preview}>
                  <Dialog.Title className={styles.previewHeading}>
                    Draft preview · no agent connection
                  </Dialog.Title>
                  <Dialog.Description className={styles.previewDescription}>
                    Unsaved structured content; no data is submitted from this
                    preview.
                  </Dialog.Description>
                  <Dialog.Close asChild>
                    <button type="button" className={styles.close}>
                      Close preview
                    </button>
                  </Dialog.Close>
                  <WebsiteRenderer
                    site={{
                      configuration,
                      template: websiteTemplates[configuration.templateId],
                      voice: {
                        kind: "preview",
                        notice:
                          "Editor preview only. No conversation is connected.",
                      },
                    }}
                  />
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            {record?.status === "published" && (
              <Link
                href={`/sites/${record.slug}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open published website ↗
              </Link>
            )}
          </div>
        </fieldset>
      </form>
    </section>
  );
}
