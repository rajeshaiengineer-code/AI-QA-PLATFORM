import { cn } from "@/lib/utils";
import type { Priority } from "@/types/story";

const styles: Record<Priority, string> = {
  critical: "bg-rose-100 text-rose-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-900",
  low: "bg-slate-100 text-slate-700",
};

const labels: Record<Priority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[priority]
      )}
    >
      {labels[priority]}
    </span>
  );
}
