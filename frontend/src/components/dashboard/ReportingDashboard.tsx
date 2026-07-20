"use client";

import { useMemo, useState } from "react";

import {
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import {
  getErrorMessage,
  useAiMetricsQuery,
  useCoverageQuery,
  useDashboardSummaryQuery,
  useExecutionTrendsQuery,
} from "@/hooks/useDashboard";
import { useProjectsQuery } from "@/hooks/useProjects";
import type { DashboardQueryParams } from "@/types/dashboard";

function pct(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">
        {value}
      </p>
    </div>
  );
}

function StatusBars({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const entries = Object.entries(data);
  const max = Math.max(1, ...entries.map(([, n]) => n));

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {entries.length === 0 ? (
        <p className="mt-3 text-sm text-muted">No data yet.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {entries.map(([key, count]) => (
            <li key={key}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="capitalize text-muted">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="font-semibold tabular-nums text-foreground">
                  {count}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function TrendBars({
  buckets,
}: {
  buckets: { bucket_label: string; passed: number; failed: number; total: number }[];
}) {
  const recent = buckets.slice(-14);
  const max = Math.max(1, ...recent.map((b) => b.total));

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <h3 className="text-sm font-semibold text-foreground">
        Execution trends (last {recent.length} days)
      </h3>
      {recent.every((b) => b.total === 0) ? (
        <p className="mt-3 text-sm text-muted">No executions in this window.</p>
      ) : (
        <div className="mt-4 flex h-36 items-end gap-1.5">
          {recent.map((bucket) => {
            const height = `${(bucket.total / max) * 100}%`;
            const failShare =
              bucket.total > 0 ? (bucket.failed / bucket.total) * 100 : 0;
            return (
              <div
                key={bucket.bucket_label}
                className="group relative flex min-w-0 flex-1 flex-col justify-end"
                title={`${bucket.bucket_label}: ${bucket.passed} passed, ${bucket.failed} failed`}
              >
                <div
                  className="w-full overflow-hidden rounded-t bg-accent/25"
                  style={{ height }}
                >
                  <div
                    className="w-full bg-danger/70"
                    style={{ height: `${failShare}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <p className="mt-3 text-xs text-muted">
        Teal = volume; red segment ≈ failed share within each day.
      </p>
    </section>
  );
}

export function ReportingDashboard() {
  const [projectId, setProjectId] = useState("");
  const projectsQuery = useProjectsQuery({
    page: 1,
    page_size: 100,
    search: "",
    organization_id: "",
    is_active: "",
  });

  const params: DashboardQueryParams = useMemo(
    () => (projectId ? { project_id: projectId, days: 30, bucket: "day" } : { days: 30, bucket: "day" }),
    [projectId]
  );

  const summaryQuery = useDashboardSummaryQuery(params);
  const trendsQuery = useExecutionTrendsQuery(params);
  const coverageQuery = useCoverageQuery(params);
  const aiQuery = useAiMetricsQuery(params);

  const loading =
    summaryQuery.isLoading ||
    trendsQuery.isLoading ||
    coverageQuery.isLoading ||
    aiQuery.isLoading;

  const error =
    summaryQuery.error ||
    trendsQuery.error ||
    coverageQuery.error ||
    aiQuery.error;

  if (loading && !summaryQuery.data) {
    return <LoadingState message="Loading dashboard…" />;
  }

  if (error && !summaryQuery.data) {
    return (
      <ErrorState
        title="Failed to load dashboard"
        message={getErrorMessage(error)}
        onRetry={() => {
          void summaryQuery.refetch();
          void trendsQuery.refetch();
          void coverageQuery.refetch();
          void aiQuery.refetch();
        }}
      />
    );
  }

  const summary = summaryQuery.data;
  const coverage = coverageQuery.data;
  const ai = aiQuery.data;
  const trends = trendsQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            Quality overview
          </h2>
          <p className="mt-1 text-sm text-muted">
            Counts and ratios across stories, tests, executions, and AI artifacts.
          </p>
        </div>
        <label className="block text-sm">
          <span className="mb-1 block text-xs font-medium text-muted">
            Project scope
          </span>
          <select
            className="min-w-[220px] rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <option value="">All projects</option>
            {(projectsQuery.data?.items ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.key} — {project.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Projects" value={String(summary?.project_count ?? 0)} />
        <StatCard label="Sprints" value={String(summary?.sprint_count ?? 0)} />
        <StatCard label="Stories" value={String(summary?.story_count ?? 0)} />
        <StatCard
          label="Test cases"
          value={String(summary?.test_case_count ?? 0)}
        />
        <StatCard
          label="Executions"
          value={String(summary?.execution_count ?? 0)}
        />
        <StatCard
          label="Jobs"
          value={String(summary?.automation_job_count ?? 0)}
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <StatusBars
          title="Stories by status"
          data={summary?.stories_by_status ?? {}}
        />
        <StatusBars
          title="Executions by status"
          data={summary?.executions_by_status ?? {}}
        />
      </div>

      <TrendBars buckets={trends?.buckets ?? []} />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-surface p-5">
          <h3 className="text-sm font-semibold text-foreground">Coverage</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <StatCard
              label="With tests"
              value={String(coverage?.stories_with_test_cases ?? 0)}
            />
            <StatCard
              label="Without tests"
              value={String(coverage?.stories_without_test_cases ?? 0)}
            />
            <StatCard
              label="Coverage"
              value={pct(coverage?.coverage_ratio ?? 0)}
            />
            <StatCard
              label="Approved"
              value={pct(coverage?.approved_ratio ?? 0)}
            />
          </div>
          <ul className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <li className="rounded-md bg-surface-muted px-3 py-2">
              <span className="text-muted">Approved</span>
              <p className="font-semibold tabular-nums">
                {coverage?.test_cases_approved ?? 0}
              </p>
            </li>
            <li className="rounded-md bg-surface-muted px-3 py-2">
              <span className="text-muted">Pending</span>
              <p className="font-semibold tabular-nums">
                {coverage?.test_cases_pending_review ?? 0}
              </p>
            </li>
            <li className="rounded-md bg-surface-muted px-3 py-2">
              <span className="text-muted">Draft</span>
              <p className="font-semibold tabular-nums">
                {coverage?.test_cases_draft ?? 0}
              </p>
            </li>
            <li className="rounded-md bg-surface-muted px-3 py-2">
              <span className="text-muted">Rejected</span>
              <p className="font-semibold tabular-nums">
                {coverage?.test_cases_rejected ?? 0}
              </p>
            </li>
          </ul>
        </section>

        <section className="rounded-lg border border-border bg-surface p-5">
          <h3 className="text-sm font-semibold text-foreground">AI metrics</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <StatCard
              label="Analyses"
              value={String(ai?.analyses_count ?? 0)}
            />
            <StatCard
              label="AI test cases"
              value={String(ai?.generated_test_cases ?? 0)}
            />
            <StatCard
              label="BDD artifacts"
              value={String(ai?.bdd_artifacts ?? 0)}
            />
            <StatCard
              label="Playwright"
              value={String(ai?.playwright_artifacts ?? 0)}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
