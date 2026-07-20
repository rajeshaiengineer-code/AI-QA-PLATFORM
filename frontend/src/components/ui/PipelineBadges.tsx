"use client";

import { cn } from "@/lib/utils";
import type { TestCaseStatus } from "@/types/testcase";
import type { ExecutionStatus } from "@/types/automation";

const testCaseStyles: Record<TestCaseStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  pending_review: "bg-amber-100 text-amber-900",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-800",
};

const testCaseLabels: Record<TestCaseStatus, string> = {
  draft: "Draft",
  pending_review: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
};

export function TestCaseStatusBadge({ status }: { status: TestCaseStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        testCaseStyles[status] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {testCaseLabels[status] ?? status}
    </span>
  );
}

const executionStyles: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  running: "bg-sky-100 text-sky-800",
  passed: "bg-emerald-100 text-emerald-800",
  failed: "bg-rose-100 text-rose-800",
  skipped: "bg-slate-100 text-slate-600",
  error: "bg-rose-100 text-rose-900",
  blocked: "bg-amber-100 text-amber-900",
};

export function ExecutionStatusBadge({ status }: { status: ExecutionStatus | string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        executionStyles[status] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
