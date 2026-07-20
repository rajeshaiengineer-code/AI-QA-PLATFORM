"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import {
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import {
  getErrorMessage,
  useProjectDashboardQuery,
  useProjectQuery,
} from "@/hooks/useProjects";
import { ROUTES } from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";

export function ProjectDetail({ projectId }: { projectId: string }) {
  const projectQuery = useProjectQuery(projectId);
  const statsQuery = useProjectDashboardQuery(projectId);

  if (projectQuery.isLoading) {
    return <LoadingState message="Loading project…" />;
  }

  if (projectQuery.isError || !projectQuery.data) {
    return (
      <ErrorState
        title="Failed to load project"
        message={getErrorMessage(projectQuery.error)}
        onRetry={() => void projectQuery.refetch()}
      />
    );
  }

  const project = projectQuery.data;
  const stats = statsQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-xs text-muted">{project.key}</p>
          <h2 className="mt-1 text-2xl font-semibold text-foreground">
            {project.name}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            {project.description || "No description"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={ROUTES.PROJECTS}>
            <Button variant="secondary">Back to projects</Button>
          </Link>
          <Link href={`${ROUTES.SPRINTS}?project_id=${project.id}`}>
            <Button variant="secondary">View sprints</Button>
          </Link>
          <Link href={`${ROUTES.STORIES}?project_id=${project.id}`}>
            <Button>View stories</Button>
          </Link>
        </div>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Stories"
          value={statsQuery.isLoading ? "…" : String(stats?.story_total ?? 0)}
        />
        <StatCard
          label="Sprints"
          value={statsQuery.isLoading ? "…" : String(stats?.sprint_total ?? 0)}
        />
        <StatCard
          label="Active sprints"
          value={
            statsQuery.isLoading
              ? "…"
              : String(stats?.active_sprint_total ?? 0)
          }
        />
        <StatCard
          label="Status"
          value={project.is_active ? "Active" : "Inactive"}
        />
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <h3 className="text-sm font-semibold text-foreground">
          Stories by status
        </h3>
        {statsQuery.isLoading ? (
          <p className="mt-3 text-sm text-muted">Loading stats…</p>
        ) : statsQuery.isError ? (
          <p className="mt-3 text-sm text-danger">
            {getErrorMessage(statsQuery.error)}
          </p>
        ) : Object.keys(stats?.story_by_status ?? {}).length === 0 ? (
          <p className="mt-3 text-sm text-muted">No stories in this project.</p>
        ) : (
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(stats?.story_by_status ?? {}).map(
              ([status, count]) => (
                <li
                  key={status}
                  className="flex items-center justify-between rounded-md bg-surface-muted px-3 py-2 text-sm"
                >
                  <span className="capitalize text-muted">
                    {status.replace("_", " ")}
                  </span>
                  <span className="font-semibold text-foreground">{count}</span>
                </li>
              )
            )}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <h3 className="text-sm font-semibold text-foreground">Metadata</h3>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Organization</dt>
            <dd className="mt-1 font-mono text-xs">{project.organization_id}</dd>
          </div>
          <div>
            <dt className="text-muted">External ID</dt>
            <dd className="mt-1 font-mono text-xs">
              {project.external_id || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Created</dt>
            <dd className="mt-1">{formatDateTime(project.created_at)}</dd>
          </div>
          <div>
            <dt className="text-muted">Updated</dt>
            <dd className="mt-1">{formatDateTime(project.updated_at)}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
    </div>
  );
}
