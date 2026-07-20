"use client";

import { Button } from "@/components/ui/Button";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { PriorityBadge } from "@/components/ui/PriorityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/utils";
import { useStoryStore } from "@/store/story.store";
import type { Story } from "@/types/story";

interface StoryTableProps {
  stories: Story[];
}

export function StoryTable({ stories }: StoryTableProps) {
  const { openDetails, openEdit, openDelete } = useStoryStore();

  const columns: DataTableColumn<Story>[] = [
    {
      key: "key",
      header: "Key",
      className: "w-28",
      render: (row) => (
        <span className="font-mono text-xs text-muted">
          {row.external_id || "—"}
        </span>
      ),
    },
    {
      key: "title",
      header: "Title",
      render: (row) => (
        <div className="min-w-48 max-w-md">
          <p className="font-medium text-foreground">{row.title}</p>
          <p className="truncate text-xs text-muted capitalize">
            {row.story_type.replace("_", " ")}
          </p>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "priority",
      header: "Priority",
      render: (row) => <PriorityBadge priority={row.priority} />,
    },
    {
      key: "points",
      header: "Points",
      className: "w-20",
      render: (row) => row.story_points ?? "—",
    },
    {
      key: "updated",
      header: "Updated",
      className: "whitespace-nowrap",
      render: (row) => formatDate(row.updated_at),
    },
    {
      key: "actions",
      header: "Actions",
      className: "w-40",
      render: (row) => (
        <div
          className="flex items-center gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => openDetails(row)}
          >
            View
          </Button>
          <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-danger"
            onClick={() => openDelete(row)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={stories}
      rowKey={(row) => row.id}
      onRowClick={openDetails}
      emptyMessage="No stories match your filters."
    />
  );
}
