"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { PriorityBadge } from "@/components/ui/PriorityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ROUTES } from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import { useAnalyzeStory, useGenerateTestCases } from "@/hooks/useTestCases";
import { getErrorMessage } from "@/hooks/useStories";
import { useStoryStore } from "@/store/story.store";

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-3 border-b border-border py-3 text-sm last:border-b-0">
      <dt className="text-muted">{label}</dt>
      <dd className="break-words text-foreground">{children}</dd>
    </div>
  );
}

export function StoryDetailsDrawer() {
  const {
    isDrawerOpen,
    selectedStory,
    closeDrawer,
    openEdit,
    openDelete,
  } = useStoryStore();

  const analyzeMutation = useAnalyzeStory();
  const generateMutation = useGenerateTestCases();
  const [aiMessage, setAiMessage] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  if (!selectedStory) return null;

  const story = selectedStory;

  return (
    <Drawer
      open={isDrawerOpen}
      title="Story details"
      onClose={closeDrawer}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={() => openEdit(story)}>
            Edit
          </Button>
          <Button variant="danger" onClick={() => openDelete(story)}>
            Delete
          </Button>
        </div>
      }
    >
      <div className="mb-4 space-y-2 rounded-md border border-border bg-surface-muted/40 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
          AI &amp; QA actions
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            loading={analyzeMutation.isPending}
            onClick={async () => {
              setAiError(null);
              setAiMessage(null);
              try {
                const res = await analyzeMutation.mutateAsync(story.id);
                setAiMessage(
                  res.summary
                    ? `Analysis: ${res.summary.slice(0, 160)}…`
                    : "Story analyzed"
                );
              } catch (e) {
                setAiError(getErrorMessage(e));
              }
            }}
          >
            Analyze story
          </Button>
          <Button
            size="sm"
            variant="secondary"
            loading={generateMutation.isPending}
            onClick={async () => {
              setAiError(null);
              setAiMessage(null);
              try {
                const res = await generateMutation.mutateAsync({
                  storyId: story.id,
                });
                setAiMessage(`Generated ${res.count} test case(s)`);
              } catch (e) {
                setAiError(getErrorMessage(e));
              }
            }}
          >
            Generate tests
          </Button>
          <Link
            href={`${ROUTES.TEST_CASES}`}
            className="inline-flex h-8 items-center rounded-md border border-border px-3 text-xs font-medium hover:bg-surface-muted"
          >
            Open Test Cases
          </Link>
          <Link
            href={ROUTES.AUTOMATION}
            className="inline-flex h-8 items-center rounded-md border border-border px-3 text-xs font-medium hover:bg-surface-muted"
          >
            Open Automation
          </Link>
        </div>
        {aiError ? <p className="text-xs text-danger">{aiError}</p> : null}
        {aiMessage ? (
          <p className="text-xs text-emerald-800">{aiMessage}</p>
        ) : null}
      </div>

      <dl>
        <DetailRow label="Title">{story.title}</DetailRow>
        <DetailRow label="Key">{story.external_id || "—"}</DetailRow>
        <DetailRow label="Jira ID">{story.jira_issue_id || "—"}</DetailRow>
        <DetailRow label="Status">
          <StatusBadge status={story.status} />
        </DetailRow>
        <DetailRow label="Priority">
          <PriorityBadge priority={story.priority} />
        </DetailRow>
        <DetailRow label="Type">
          <span className="capitalize">
            {story.story_type.replace("_", " ")}
          </span>
        </DetailRow>
        <DetailRow label="Assignee">{story.assignee || "—"}</DetailRow>
        <DetailRow label="Reporter">{story.reporter || "—"}</DetailRow>
        <DetailRow label="Labels">
          {story.labels?.length ? (
            <span className="flex flex-wrap gap-1">
              {story.labels.map((label) => (
                <span
                  key={label}
                  className="rounded bg-surface-muted px-1.5 py-0.5 text-xs"
                >
                  {label}
                </span>
              ))}
            </span>
          ) : (
            "—"
          )}
        </DetailRow>
        <DetailRow label="Points">{story.story_points ?? "—"}</DetailRow>
        <DetailRow label="Rank">{story.rank ?? "—"}</DetailRow>
        <DetailRow label="Project">
          <span className="font-mono text-xs">{story.project_id}</span>
        </DetailRow>
        <DetailRow label="Sprint">
          <span className="font-mono text-xs">
            {story.sprint_id || "—"}
          </span>
        </DetailRow>
        <DetailRow label="Description">
          <p className="whitespace-pre-wrap">
            {story.description || "No description"}
          </p>
        </DetailRow>
        <DetailRow label="Source updated">
          {story.external_updated_at
            ? formatDateTime(story.external_updated_at)
            : "—"}
        </DetailRow>
        <DetailRow label="Created">{formatDateTime(story.created_at)}</DetailRow>
        <DetailRow label="Updated">{formatDateTime(story.updated_at)}</DetailRow>
        <DetailRow label="Version">{story.version}</DetailRow>
      </dl>
    </Drawer>
  );
}
