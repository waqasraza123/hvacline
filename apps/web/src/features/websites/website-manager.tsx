"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { requestApi } from "@/features/operations/api";
import { websiteAsset } from "./assets";
import { WebsiteContentEditor } from "./content-editor";
import { newWebsiteConfiguration } from "./editor";
import type {
  ResolvedWebsite,
  TemplateId,
  WebsiteConfiguration,
} from "./contracts";
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
  published_version_id: string | null;
  agent_binding_id: string | null;
  knowledge_faq_ids: string[];
  voice_enabled: boolean;
  lead_capture_enabled: boolean;
};
type Version = {
  id: string;
  number: number;
  created_at: string;
  active: boolean;
  brand_name: string;
};
type Management = {
  websites: WebsiteRecord[];
  agents: { id: string; label: string; enabled: boolean }[];
  knowledge: { id: string; question: string }[];
};
type Confirmation = {
  action: "publish" | "unpublish" | "restore";
  version?: Version;
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
  const [agent, setAgent] = useState("");
  const [knowledge, setKnowledge] = useState<string[]>([]);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [leadCapture, setLeadCapture] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState<ResolvedWebsite>();
  const [confirmation, setConfirmation] = useState<Confirmation>();
  const [versions, setVersions] = useState<Version[]>();
  const [historyError, setHistoryError] = useState("");
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
  useEffect(() => {
    if (!record) return;
    let active = true;
    void requestApi<Version[]>(
      apiBaseUrl,
      token,
      `websites/${record.id}/versions`,
    )
      .then((data) => {
        if (active) setVersions(data);
      })
      .catch((failure: unknown) => {
        if (active)
          setHistoryError(
            failure instanceof Error
              ? failure.message
              : "Version history is unavailable.",
          );
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, token, record, reload]);

  function choose(next?: WebsiteRecord) {
    if (busyRef.current) return;
    try {
      const parsed = next
        ? validateWebsiteConfiguration(next.configuration)
        : newWebsiteConfiguration("industrial");
      setRecord(next ? { ...next, configuration: parsed } : undefined);
      setConfiguration(parsed);
      setAgent(next?.agent_binding_id ?? "");
      setKnowledge(next?.knowledge_faq_ids ?? []);
      setVoiceEnabled(next?.voice_enabled ?? false);
      setLeadCapture(next?.lead_capture_enabled ?? false);
      setVersions(undefined);
      setHistoryError("");
      setMessage("");
      setError("");
    } catch {
      setError(
        "This website has invalid saved content. Contact the workspace administrator.",
      );
    }
  }
  function saved(next: WebsiteRecord) {
    const parsed = validateWebsiteConfiguration(next.configuration);
    const normalized = { ...next, configuration: parsed };
    setRecord(normalized);
    setConfiguration(parsed);
    setManagement(
      (current) =>
        current && {
          ...current,
          websites: [
            normalized,
            ...current.websites.filter((site) => site.id !== next.id),
          ],
        },
    );
    setVersions(undefined);
    setHistoryError("");
  }
  const dirty =
    !record ||
    JSON.stringify(configuration) !== JSON.stringify(record.configuration) ||
    agent !== (record.agent_binding_id ?? "") ||
    JSON.stringify(knowledge) !== JSON.stringify(record.knowledge_faq_ids) ||
    voiceEnabled !== record.voice_enabled ||
    leadCapture !== record.lead_capture_enabled;

  async function save(event: FormEvent) {
    event.preventDefault();
    if (busyRef.current) return;
    busyRef.current = true;
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
          status: "draft",
          agent_binding_id: agent || null,
          knowledge_faq_ids: knowledge,
          voice_enabled: voiceEnabled,
          lead_capture_enabled: leadCapture,
        },
      );
      saved(next);
      setMessage("Draft saved. The live website has not changed.");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Could not save. Reload before retrying a version conflict.",
      );
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  async function publish() {
    if (!record || !confirmation || busyRef.current || dirty) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const path =
        confirmation.action === "restore"
          ? `versions/${confirmation.version!.id}/restore`
          : confirmation.action;
      const next = await requestApi<WebsiteRecord>(
        apiBaseUrl,
        token,
        `websites/${record.id}/${path}`,
        "POST",
        { expected_row_version: record.row_version },
      );
      saved(next);
      setConfirmation(undefined);
      setMessage(
        confirmation.action === "unpublish"
          ? "Website unpublished. Its URL and new sessions are unavailable."
          : confirmation.action === "restore"
            ? "Previous publication restored as a new version. Your saved draft is unchanged."
            : "Website published. Share its website link below.",
      );
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Publication failed. Reload before retrying.",
      );
      setConfirmation(undefined);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  function openPreview() {
    try {
      const parsed = validateWebsiteConfiguration(configuration);
      validateTemplateCompatibility(
        parsed,
        websiteTemplates[parsed.templateId],
      );
      setPreview({
        configuration: parsed,
        template: websiteTemplates[parsed.templateId],
        voice: {
          kind: "preview",
          notice: "Draft preview. No conversation is connected.",
        },
      });
      setError("");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Fix draft validation before previewing.",
      );
    }
  }
  async function reloadSaved() {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const data = await requestApi<Management>(apiBaseUrl, token, "websites");
      setManagement(data);
      const next = data.websites.find((site) => site.id === record?.id);
      if (next) saved(next);
      setError("");
      setMessage("Saved draft reloaded.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Reload failed.");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  return (
    <section className="ops-card">
      <div className={styles.heading}>
        <div>
          <p className="section-help">RESTRICTED BUSINESS WORKSPACE</p>
          <h2>Your websites</h2>
          <p>Customize a draft, preview it and publish when ready.</p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (
              !dirty ||
              window.confirm("Discard unsaved changes and create a website?")
            )
              choose();
          }}
        >
          Create website
        </button>
      </div>
      {!management && !error && <p role="status">Loading your websites…</p>}
      {management?.websites.length === 0 && (
        <p>No websites yet. Start with a template below.</p>
      )}
      <div className={styles.siteGallery}>
        {management?.websites.map((site) => (
          <button
            type="button"
            key={site.id}
            className={styles.siteCard}
            disabled={busy}
            aria-pressed={site.id === record?.id}
            onClick={() => {
              if (
                !dirty ||
                window.confirm("Discard unsaved changes and open this website?")
              )
                choose(site);
            }}
          >
            <Image
              src={websiteAsset(site.configuration.hero.image).src}
              alt=""
              width={240}
              height={140}
              sizes="(max-width: 640px) 100vw, 240px"
            />
            <strong>{site.configuration.brand.name}</strong>
            <span>
              {site.status} · {site.slug}
            </span>
            <small>Saved draft · {site.configuration.templateId}</small>
          </button>
        ))}
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
              Retry loading
            </button>
          )}
        </div>
      )}
      {message && (
        <p role="status" className="ops-message">
          {message}
        </p>
      )}
      {record && (
        <div className={styles.selection}>
          <span>
            {record.status === "published"
              ? "Live publication available"
              : record.status === "disabled"
                ? "Unpublished"
                : "Draft only"}{" "}
            · revision {record.row_version}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              if (
                !dirty ||
                window.confirm(
                  "Discard unsaved changes and reload the saved draft?",
                )
              )
                void reloadSaved();
            }}
          >
            Reload saved draft
          </button>
        </div>
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
              <small>
                Unique and permanent. Published URL: /sites/
                {configuration.slug || "your-slug"}
              </small>
            </label>
            <label>
              Template
              <select
                value={configuration.templateId}
                onChange={(event) => {
                  if (
                    window.confirm(
                      "Replace this draft’s content with the selected template defaults? The live publication is unchanged.",
                    )
                  )
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
            </label>
          </div>
          <WebsiteContentEditor
            configuration={configuration}
            setConfiguration={setConfiguration}
          />
          <details className={styles.editorSection} open>
            <summary>Agent & approved knowledge</summary>
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
              Enable Voice and Text
            </label>
            <label>
              <input
                type="checkbox"
                checked={leadCapture}
                onChange={(event) => setLeadCapture(event.target.checked)}
              />
              Allow customer-confirmed inquiries for human follow-up
            </label>
            <p className="section-help">
              Website booking and persistent memory are unavailable. Agents
              require server-side setup. Public page FAQs do not automatically
              become approved agent knowledge.
            </p>
            <fieldset>
              <legend>Approved assistant knowledge</legend>
              {management?.knowledge.length === 0 && (
                <p>
                  No approved answers. Add them in Knowledge before selecting
                  them here.
                </p>
              )}
              {management?.knowledge.map((faq) => (
                <label key={faq.id}>
                  <input
                    type="checkbox"
                    checked={knowledge.includes(faq.id)}
                    onChange={(event) =>
                      setKnowledge(
                        event.target.checked
                          ? [...knowledge, faq.id]
                          : knowledge.filter((id) => id !== faq.id),
                      )
                    }
                  />
                  {faq.question}
                </label>
              ))}
            </fieldset>
            <small>An empty selection exposes no knowledge records.</small>
          </details>
          <p className="section-help">
            Website management requires the administrator workspace token for the configured business; customer sign-in does not grant management access.
            Review example business content before publication.
          </p>
          <div className={styles.actions}>
            <button className="primary-link" type="submit">
              {busy ? "Saving…" : "Save draft"}
            </button>
            <button type="button" onClick={openPreview}>
              Preview draft
            </button>
          </div>
        </fieldset>
      </form>
      {record && (
        <div className={styles.publication}>
          <h3>Publication</h3>
          <p>
            {dirty
              ? "Save or reload your draft before publishing or restoring a version."
              : "Publishing makes the saved draft public at its website URL."}
          </p>
          <div className={styles.actions}>
            <button
              type="button"
              disabled={busy || dirty}
              onClick={() => setConfirmation({ action: "publish" })}
            >
              Publish saved draft
            </button>
            <button
              type="button"
              disabled={busy || dirty || record.status !== "published"}
              onClick={() => setConfirmation({ action: "unpublish" })}
            >
              Unpublish website
            </button>
            {record.status === "published" && (
              <>
                <Link
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`/sites/${record.slug}`}
                >
                  Open /sites/{record.slug} ↗
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard
                      .writeText(
                        new URL(`/sites/${record.slug}`, window.location.origin)
                          .href,
                      )
                      .then(() => setMessage("Published website URL copied."))
                      .catch(() =>
                        setError(
                          "Copy unavailable. Open the website and copy its address.",
                        ),
                      );
                  }}
                >
                  Copy share link
                </button>
              </>
            )}
          </div>
          <h3>Published version history</h3>
          {!versions && !historyError && <p role="status">Loading versions…</p>}
          {historyError && (
            <p role="alert">
              {historyError}
              <button
                type="button"
                onClick={() => {
                  setHistoryError("");
                  setReload((value) => value + 1);
                }}
              >
                Retry history
              </button>
            </p>
          )}
          {versions?.length === 0 && <p>No published versions yet.</p>}
          <ul className={styles.history}>
            {versions?.map((version) => (
              <li key={version.id}>
                <div>
                  <strong>
                    Version {version.number}
                    {version.active ? " · live" : ""}
                  </strong>
                  <span>
                    {version.brand_name} ·{" "}
                    {new Date(version.created_at).toLocaleString()}
                  </span>
                </div>
                <button
                  type="button"
                  disabled={busy || dirty || version.active}
                  onClick={() =>
                    setConfirmation({ action: "restore", version })
                  }
                >
                  Restore version {version.number}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Dialog.Root
        open={!!preview}
        onOpenChange={(open) => {
          if (!open) setPreview(undefined);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className={styles.overlay} />
          <Dialog.Content className={styles.preview}>
            <Dialog.Title className={styles.previewHeading}>
              Draft preview
            </Dialog.Title>
            <Dialog.Description className={styles.previewDescription}>
              This preview cannot start an agent. Nothing is published.
            </Dialog.Description>
            <Dialog.Close className={styles.close}>Close preview</Dialog.Close>
            {preview && <WebsiteRenderer site={preview} />}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      <Dialog.Root
        open={!!confirmation}
        onOpenChange={(open) => {
          if (!open && !busy) setConfirmation(undefined);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className={styles.overlay} />
          <Dialog.Content
            className={styles.confirmation}
            onEscapeKeyDown={(event) => {
              if (busy) event.preventDefault();
            }}
            onPointerDownOutside={(event) => {
              if (busy) event.preventDefault();
            }}
          >
            <Dialog.Title>
              {confirmation?.action === "restore"
                ? `Restore version ${confirmation.version?.number}?`
                : confirmation?.action === "unpublish"
                  ? "Unpublish this website?"
                  : "Publish this saved draft?"}
            </Dialog.Title>
            <Dialog.Description>
              {confirmation?.action === "restore"
                ? "This creates a new live publication from the selected version. The saved draft stays unchanged. Agent and knowledge permissions are checked again."
                : confirmation?.action === "unpublish"
                  ? "The public URL and new Voice/Text sessions become unavailable. Saved drafts and versions are retained."
                  : "Your saved content and enabled capabilities become publicly available. Existing website conversations must restart after publication."}
            </Dialog.Description>
            <div className={styles.actions}>
              <button
                type="button"
                disabled={busy}
                onClick={() => void publish()}
              >
                {busy ? "Applying…" : "Confirm"}
              </button>
              <Dialog.Close disabled={busy}>Cancel</Dialog.Close>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
