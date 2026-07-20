"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Drawer } from "@/components/ui/Drawer";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import { PriorityBadge } from "@/components/ui/PriorityBadge";
import { TestCaseStatusBadge } from "@/components/ui/PipelineBadges";
import { Select } from "@/components/ui/Select";
import { getErrorMessage } from "@/hooks/useStories";
import {
  useApproveAllTestCases,
  useApproveTestCase,
  useGenerateTestCases,
  useRejectTestCase,
  useStoryTestCases,
} from "@/hooks/useTestCases";
import { useStoriesQuery } from "@/hooks/useStories";
import type { TestCase } from "@/types/testcase";
import type { Priority } from "@/types/story";

export function TestCaseDashboard() {
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
  const [storyId, setStoryId] = useState<string>("");
  const [selected, setSelected] = useState<TestCase | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionOk, setActionOk] = useState<string | null>(null);

  const listQuery = useStoryTestCases(storyId || null);
  const generateMutation = useGenerateTestCases();
  const approveMutation = useApproveTestCase();
  const rejectMutation = useRejectTestCase();
  const approveAllMutation = useApproveAllTestCases();

  const cases = useMemo(() => listQuery.data?.items ?? [], [listQuery.data]);

  const storyOptions = stories.map((s) => ({
    value: s.id,
    label: `${s.external_id || s.id.slice(0, 8)} — ${s.title}`,
  }));

  const columns: DataTableColumn<TestCase>[] = [
    {
      key: "title",
      header: "Title",
      render: (row) => (
        <button
          type="button"
          className="text-left font-medium text-accent hover:underline"
          onClick={() => setSelected(row)}
        >
          {row.title}
        </button>
      ),
    },
    {
      key: "category",
      header: "Category",
      render: (row) => (
        <span className="capitalize text-muted">{row.category || "—"}</span>
      ),
    },
    {
      key: "priority",
      header: "Priority",
      render: (row) => (
        <PriorityBadge priority={row.priority as Priority} />
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <TestCaseStatusBadge status={row.status} />,
    },
    {
      key: "source",
      header: "Source",
      render: (row) => <span className="capitalize">{row.source}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          <Button
            size="sm"
            variant="secondary"
            disabled={
              row.status === "approved" || approveMutation.isPending
            }
            onClick={async () => {
              setActionError(null);
              try {
                await approveMutation.mutateAsync(row.id);
                setActionOk(`Approved: ${row.title}`);
              } catch (e) {
                setActionError(getErrorMessage(e));
              }
            }}
          >
            Approve
          </Button>
          <Button
            size="sm"
            variant="danger"
            disabled={
              row.status === "rejected" || rejectMutation.isPending
            }
            onClick={async () => {
              setActionError(null);
              try {
                await rejectMutation.mutateAsync({
                  id: row.id,
                  reason: "Rejected from Test Cases UI",
                });
                setActionOk(`Rejected: ${row.title}`);
              } catch (e) {
                setActionError(getErrorMessage(e));
              }
            }}
          >
            Reject
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="w-full max-w-xl">
          <Select
            label="Story"
            placeholder="Select a story"
            options={storyOptions}
            value={storyId}
            onChange={(e) => {
              setStoryId(e.target.value);
              setSelected(null);
              setActionError(null);
              setActionOk(null);
            }}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={!storyId || generateMutation.isPending}
            loading={generateMutation.isPending}
            onClick={async () => {
              setActionError(null);
              setActionOk(null);
              try {
                const res = await generateMutation.mutateAsync({ storyId });
                setActionOk(
                  `Generated ${res.count} test case${res.count === 1 ? "" : "s"}`
                );
              } catch (e) {
                setActionError(getErrorMessage(e));
              }
            }}
          >
            Generate with AI
          </Button>
          <Button
            variant="secondary"
            disabled={!storyId || approveAllMutation.isPending}
            loading={approveAllMutation.isPending}
            onClick={async () => {
              setActionError(null);
              try {
                const res = await approveAllMutation.mutateAsync(storyId);
                setActionOk(`Approved ${res.approved_count} case(s)`);
              } catch (e) {
                setActionError(getErrorMessage(e));
              }
            }}
          >
            Approve all
          </Button>
        </div>
      </div>

      {actionError ? (
        <p className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {actionError}
        </p>
      ) : null}
      {actionOk ? (
        <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {actionOk}
        </p>
      ) : null}

      {!storyId ? (
        <EmptyState
          title="Select a story"
          description="Choose a story to list, generate, and approve test cases."
        />
      ) : listQuery.isLoading ? (
        <LoadingState message="Loading test cases…" />
      ) : listQuery.isError ? (
        <ErrorState
          message={getErrorMessage(listQuery.error)}
          onRetry={() => void listQuery.refetch()}
        />
      ) : cases.length === 0 ? (
        <EmptyState
          title="No test cases yet"
          description="Generate AI test cases for this story, or load sample seed data."
          action={
            <Button
              loading={generateMutation.isPending}
              onClick={async () => {
                try {
                  const res = await generateMutation.mutateAsync({ storyId });
                  setActionOk(`Generated ${res.count} test case(s)`);
                } catch (e) {
                  setActionError(getErrorMessage(e));
                }
              }}
            >
              Generate with AI
            </Button>
          }
        />
      ) : (
        <section className="overflow-hidden rounded-lg border border-border bg-surface">
          <DataTable columns={columns} data={cases} rowKey={(r) => r.id} />
        </section>
      )}

      <Drawer
        open={Boolean(selected)}
        title="Test case details"
        onClose={() => setSelected(null)}
        footer={
          selected ? (
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                disabled={selected.status === "approved"}
                onClick={async () => {
                  try {
                    await approveMutation.mutateAsync(selected.id);
                    setSelected(null);
                    setActionOk(`Approved: ${selected.title}`);
                  } catch (e) {
                    setActionError(getErrorMessage(e));
                  }
                }}
              >
                Approve
              </Button>
              <Button
                variant="danger"
                disabled={selected.status === "rejected"}
                onClick={async () => {
                  try {
                    await rejectMutation.mutateAsync({ id: selected.id });
                    setSelected(null);
                    setActionOk(`Rejected: ${selected.title}`);
                  } catch (e) {
                    setActionError(getErrorMessage(e));
                  }
                }}
              >
                Reject
              </Button>
            </div>
          ) : null
        }
      >
        {selected ? (
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-muted">Title</dt>
              <dd className="font-medium">{selected.title}</dd>
            </div>
            <div>
              <dt className="text-muted">Status</dt>
              <dd className="mt-1">
                <TestCaseStatusBadge status={selected.status} />
              </dd>
            </div>
            <div>
              <dt className="text-muted">Description</dt>
              <dd className="whitespace-pre-wrap">
                {selected.description || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Preconditions</dt>
              <dd className="whitespace-pre-wrap">
                {selected.preconditions || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Steps</dt>
              <dd>
                {selected.steps?.length ? (
                  <ol className="mt-1 list-decimal space-y-2 pl-5">
                    {selected.steps.map((step, i) => (
                      <li key={i}>
                        <p>{step.action}</p>
                        {step.expected ? (
                          <p className="text-muted">
                            Expected: {step.expected}
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Expected result</dt>
              <dd className="whitespace-pre-wrap">
                {selected.expected_result || "—"}
              </dd>
            </div>
            {selected.rejection_reason ? (
              <div>
                <dt className="text-muted">Rejection reason</dt>
                <dd>{selected.rejection_reason}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </Drawer>
    </div>
  );
}
