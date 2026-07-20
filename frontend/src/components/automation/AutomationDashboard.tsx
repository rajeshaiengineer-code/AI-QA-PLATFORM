"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import { ExecutionStatusBadge } from "@/components/ui/PipelineBadges";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import {
  useAnalyzeFailure,
  useCreateJiraBug,
  useExecutions,
  useGenerateBdd,
  useGeneratePlaywright,
  useRunExecution,
  useStoryBdd,
  useStoryPlaywright,
} from "@/hooks/useAutomation";
import { getErrorMessage, useStoriesQuery } from "@/hooks/useStories";
import type { Execution } from "@/types/automation";

export function AutomationDashboard() {
  const storiesQuery = useStoriesQuery({
    page: 1,
    page_size: 100,
    status: "",
    story_type: "",
    priority: "",
    project_id: "",
    sprint_id: "",
    search: "",
  });
  const stories = storiesQuery.data?.items ?? [];
  const [storyId, setStoryId] = useState("");
  const [jiraProjectKey, setJiraProjectKey] = useState("SCRUM");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [analysisByExec, setAnalysisByExec] = useState<
    Record<string, string>
  >({});

  const bddQuery = useStoryBdd(storyId || null);
  const pwQuery = useStoryPlaywright(storyId || null);
  const execQuery = useExecutions(
    lastJobId ? { automation_job_id: lastJobId } : {}
  );

  const generateBdd = useGenerateBdd();
  const generatePw = useGeneratePlaywright();
  const runExec = useRunExecution();
  const analyzeFailure = useAnalyzeFailure();
  const createBug = useCreateJiraBug();

  const storyOptions = stories.map((s) => ({
    value: s.id,
    label: `${s.external_id || s.id.slice(0, 8)} — ${s.title}`,
  }));

  const bddFeatures = bddQuery.data?.items ?? [];
  const artifacts = pwQuery.data?.items ?? [];
  const executions = useMemo(
    () => execQuery.data?.items ?? [],
    [execQuery.data]
  );

  const columns: DataTableColumn<Execution>[] = [
    {
      key: "id",
      header: "Execution",
      render: (row) => (
        <span className="font-mono text-xs">{row.id.slice(0, 8)}…</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <ExecutionStatusBadge status={row.status} />,
    },
    {
      key: "duration",
      header: "Duration",
      render: (row) =>
        row.duration_ms != null ? `${row.duration_ms} ms` : "—",
    },
    {
      key: "error",
      header: "Error",
      render: (row) => (
        <span className="line-clamp-2 max-w-xs text-xs text-muted">
          {row.error_message || "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => {
        const failed =
          row.status === "failed" ||
          row.status === "error" ||
          row.status === "blocked";
        return (
          <div className="flex flex-wrap gap-1">
            <Button
              size="sm"
              variant="secondary"
              disabled={!failed || analyzeFailure.isPending}
              onClick={async () => {
                setError(null);
                try {
                  const res = await analyzeFailure.mutateAsync(row.id);
                  setAnalysisByExec((prev) => ({
                    ...prev,
                    [row.id]: res.id,
                  }));
                  setMessage(
                    `Analysis: ${res.summary.slice(0, 120)}${res.summary.length > 120 ? "…" : ""}`
                  );
                } catch (e) {
                  setError(getErrorMessage(e));
                }
              }}
            >
              Analyze
            </Button>
            <Button
              size="sm"
              disabled={!failed || createBug.isPending}
              onClick={async () => {
                setError(null);
                try {
                  const res = await createBug.mutateAsync({
                    executionId: row.id,
                    payload: {
                      jira_project_key: jiraProjectKey || "SCRUM",
                      failure_analysis_id: analysisByExec[row.id],
                    },
                  });
                  setMessage(
                    `Jira bug created: ${res.jira_key}${res.jira_url ? ` (${res.jira_url})` : ""}`
                  );
                } catch (e) {
                  setError(getErrorMessage(e));
                }
              }}
            >
              Create Jira bug
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted">
        Pipeline: generate BDD → Playwright artifacts → run suite (stub or
        local Playwright) → analyze failures → file Jira bugs.
      </p>

      <div className="grid gap-4 lg:grid-cols-[1fr_12rem]">
        <Select
          label="Story"
          placeholder="Select a story"
          options={storyOptions}
          value={storyId}
          onChange={(e) => {
            setStoryId(e.target.value);
            setLastJobId(null);
            setMessage(null);
            setError(null);
          }}
        />
        <Input
          label="Jira project key"
          value={jiraProjectKey}
          onChange={(e) => setJiraProjectKey(e.target.value.toUpperCase())}
          placeholder="SCRUM"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          disabled={!storyId || generateBdd.isPending}
          loading={generateBdd.isPending}
          onClick={async () => {
            setError(null);
            try {
              const res = await generateBdd.mutateAsync({ storyId });
              setMessage(`BDD generated: ${res.feature.name}`);
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          1. Generate BDD
        </Button>
        <Button
          disabled={!storyId || generatePw.isPending}
          loading={generatePw.isPending}
          variant="secondary"
          onClick={async () => {
            setError(null);
            try {
              const res = await generatePw.mutateAsync(storyId);
              setMessage(
                `Playwright artifact: ${res.artifact.name} (${res.file_count ?? 0} files)`
              );
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          2. Generate Playwright
        </Button>
        <Button
          disabled={!storyId || runExec.isPending}
          loading={runExec.isPending}
          onClick={async () => {
            setError(null);
            try {
              const res = await runExec.mutateAsync({
                story_id: storyId,
                include_drafts: true,
                runner: "stub",
                name: `UI stub run ${new Date().toISOString()}`,
              });
              setLastJobId(res.job.id);
              setMessage(
                `Stub run complete — passed ${res.job.passed}/${res.job.total}, failed ${res.job.failed}`
              );
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          3. Run (stub)
        </Button>
        <Button
          variant="secondary"
          disabled={!storyId || runExec.isPending || artifacts.length === 0}
          loading={runExec.isPending}
          onClick={async () => {
            setError(null);
            try {
              const artifactId = artifacts[0]?.id;
              if (!artifactId) {
                setError("Generate a Playwright artifact before running.");
                return;
              }
              const res = await runExec.mutateAsync({
                automation_artifact_id: artifactId,
                include_drafts: true,
                runner: "playwright",
                name: `UI Playwright run ${new Date().toISOString()}`,
              });
              setLastJobId(res.job.id);
              setMessage(
                `Playwright run (${res.runner}) — passed ${res.job.passed}/${res.job.total}, failed ${res.job.failed}, errors ${res.job.error}`
              );
            } catch (e) {
              setError(getErrorMessage(e));
            }
          }}
        >
          3b. Run (Playwright)
        </Button>
      </div>

      {error ? (
        <p className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {message}
        </p>
      ) : null}

      {!storyId ? (
        <EmptyState
          title="Select a story"
          description="Pick a story that has approved (or draft) test cases to automate."
        />
      ) : (
        <>
          <section className="rounded-lg border border-border bg-surface p-4">
            <h3 className="text-sm font-semibold text-foreground">
              BDD features ({bddFeatures.length})
            </h3>
            {bddQuery.isLoading ? (
              <LoadingState message="Loading BDD…" />
            ) : bddQuery.isError ? (
              <ErrorState message={getErrorMessage(bddQuery.error)} />
            ) : bddFeatures.length === 0 ? (
              <p className="mt-2 text-sm text-muted">No BDD features yet.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {bddFeatures.map((f) => (
                  <li key={f.id} className="rounded-md bg-surface-muted/50 p-3">
                    <p className="font-medium">{f.name}</p>
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-muted">
                      {f.gherkin_content.slice(0, 800)}
                      {f.gherkin_content.length > 800 ? "…" : ""}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-border bg-surface p-4">
            <h3 className="text-sm font-semibold text-foreground">
              Playwright artifacts ({artifacts.length})
            </h3>
            {pwQuery.isLoading ? (
              <LoadingState message="Loading artifacts…" />
            ) : artifacts.length === 0 ? (
              <p className="mt-2 text-sm text-muted">No artifacts yet.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {artifacts.map((a) => {
                  const fileCount =
                    (a.specs?.length ?? 0) +
                    (a.page_objects?.length ?? 0) +
                    (a.locators?.length ?? 0);
                  return (
                    <li
                      key={a.id}
                      className="flex items-center justify-between gap-3 rounded-md bg-surface-muted/50 px-3 py-2 text-sm"
                    >
                      <span className="font-medium">{a.name}</span>
                      <span className="text-muted">
                        {fileCount} file{fileCount === 1 ? "" : "s"} ·{" "}
                        {a.framework}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="overflow-hidden rounded-lg border border-border bg-surface">
            <div className="border-b border-border px-4 py-3">
              <h3 className="text-sm font-semibold">
                Executions {lastJobId ? `(job ${lastJobId.slice(0, 8)}…)` : ""}
              </h3>
            </div>
            {!lastJobId ? (
              <p className="px-4 py-8 text-center text-sm text-muted">
                Run a stub suite to see execution results here.
              </p>
            ) : execQuery.isLoading ? (
              <LoadingState message="Loading executions…" />
            ) : (
              <DataTable
                columns={columns}
                data={executions}
                rowKey={(r) => r.id}
              />
            )}
          </section>
        </>
      )}
    </div>
  );
}
