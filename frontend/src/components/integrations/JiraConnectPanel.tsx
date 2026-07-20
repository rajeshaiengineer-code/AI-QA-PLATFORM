"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { DEFAULT_ORG_ID } from "@/lib/constants";
import {
  useConnectJira,
  useDisconnectJira,
  useJiraHealth,
  useSyncJira,
} from "@/hooks/useJira";
import { getErrorMessage } from "@/hooks/useStories";

const STORAGE_KEY = "aiqa_jira_connect_form";

function loadForm() {
  if (typeof window === "undefined") {
    return {
      base_url: "https://testaiplatform.atlassian.net",
      email: "rajeshqaengineer01@gmail.com",
      api_token: "",
      project_keys: "SCRUM",
    };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as {
      base_url: string;
      email: string;
      api_token: string;
      project_keys: string;
    };
  } catch {
    /* ignore */
  }
  return {
    base_url: "https://testaiplatform.atlassian.net",
    email: "rajeshqaengineer01@gmail.com",
    api_token: "",
    project_keys: "SCRUM",
  };
}

export function JiraConnectPanel() {
  const [form, setForm] = useState(loadForm);
  const [connected, setConnected] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const health = useJiraHealth(connected);
  const connectMutation = useConnectJira();
  const disconnectMutation = useDisconnectJira();
  const syncMutation = useSyncJira();

  const saveForm = (next: typeof form) => {
    setForm(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Jira Cloud connector
          </h3>
          <p className="text-xs text-muted">
            Connect with an Atlassian API token, then sync stories from the
            current active sprint into the platform.
          </p>
        </div>
        {connected && health.data ? (
          <span className="text-xs text-emerald-700">
            Health: {health.data.status}
            {health.data.latency_ms != null
              ? ` · ${Math.round(health.data.latency_ms)}ms`
              : ""}
          </span>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Input
          label="Site URL"
          value={form.base_url}
          onChange={(e) => saveForm({ ...form, base_url: e.target.value })}
        />
        <Input
          label="Email"
          value={form.email}
          onChange={(e) => saveForm({ ...form, email: e.target.value })}
        />
        <Input
          label="API token"
          type="password"
          value={form.api_token}
          onChange={(e) => saveForm({ ...form, api_token: e.target.value })}
          placeholder="Paste Atlassian API token"
        />
        <Input
          label="Project keys (comma-separated)"
          value={form.project_keys}
          onChange={(e) =>
            saveForm({ ...form, project_keys: e.target.value.toUpperCase() })
          }
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          loading={connectMutation.isPending}
          onClick={async () => {
            setError(null);
            setMessage(null);
            try {
              const res = await connectMutation.mutateAsync({
                base_url: form.base_url.trim(),
                email: form.email.trim(),
                api_token: form.api_token.trim(),
              });
              setConnected(true);
              setMessage(
                res.message ||
                  `Connected as ${res.account_display_name || form.email}`
              );
            } catch (e) {
              setConnected(false);
              setError(getErrorMessage(e));
            }
          }}
        >
          Connect
        </Button>
        <Button
          variant="secondary"
          disabled={!connected || syncMutation.isPending}
          loading={syncMutation.isPending}
          onClick={async () => {
            setError(null);
            setMessage(null);
            try {
              const keys = form.project_keys
                .split(",")
                .map((k) => k.trim())
                .filter(Boolean);
              const res = await syncMutation.mutateAsync({
                organization_id: DEFAULT_ORG_ID,
                project_keys: keys.length ? keys : undefined,
                active_sprint_only: true,
              });
              const active =
                (res.details?.active_sprints as string[] | undefined) || [];
              const sprintLabel = active.length
                ? ` · sprint: ${active.join(", ")}`
                : " · no active sprint";
              setMessage(
                `Sync ${res.status}: created ${res.stories_created}, updated ${res.stories_updated}, skipped ${res.stories_skipped}${sprintLabel}`
              );
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          Sync active sprint
        </Button>
        <Button
          variant="ghost"
          disabled={!connected || syncMutation.isPending}
          loading={syncMutation.isPending}
          onClick={async () => {
            setError(null);
            setMessage(null);
            try {
              const keys = form.project_keys
                .split(",")
                .map((k) => k.trim())
                .filter(Boolean);
              const res = await syncMutation.mutateAsync({
                organization_id: DEFAULT_ORG_ID,
                project_keys: keys.length ? keys : undefined,
                active_sprint_only: false,
              });
              setMessage(
                `Full backlog sync ${res.status}: created ${res.stories_created}, updated ${res.stories_updated}, skipped ${res.stories_skipped}`
              );
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          Sync full backlog
        </Button>
        <Button
          variant="ghost"
          disabled={!connected || disconnectMutation.isPending}
          onClick={async () => {
            try {
              await disconnectMutation.mutateAsync();
              setConnected(false);
              setMessage("Disconnected");
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          Disconnect
        </Button>
      </div>

      {error ? (
        <p className="mt-3 text-sm text-danger">{error}</p>
      ) : null}
      {message ? (
        <p className="mt-3 text-sm text-emerald-800">{message}</p>
      ) : null}
      {message &&
      /created 0, updated 0/.test(message) &&
      /no active sprint/i.test(message) ? (
        <p className="mt-2 text-sm text-amber-800">
          No active sprint in Jira — start a sprint on the board, move stories
          into it, then sync again. Or use <strong>Sync full backlog</strong>.
        </p>
      ) : null}
    </section>
  );
}
