import { cn } from "@/lib/utils";
import type { StoryStatus } from "@/types/story";

const styles: Record<StoryStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  ready: "bg-sky-100 text-sky-800",
  in_progress: "bg-amber-100 text-amber-900",
  in_review: "bg-indigo-100 text-indigo-800",
  done: "bg-emerald-100 text-emerald-800",
  blocked: "bg-rose-100 text-rose-800",
};

const labels: Record<StoryStatus, string> = {
  draft: "Draft",
  ready: "Ready",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
  blocked: "Blocked",
};

export function StatusBadge({ status }: { status: StoryStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[status]
      )}
    >
      {labels[status]}
    </span>
  );
}
