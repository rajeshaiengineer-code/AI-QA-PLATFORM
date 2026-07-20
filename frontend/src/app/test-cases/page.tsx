import type { Metadata } from "next";
import { Suspense } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { TestCaseDashboard } from "@/components/testcases/TestCaseDashboard";
import { LoadingState } from "@/components/ui/Feedback";

export const metadata: Metadata = {
  title: "Test Cases",
};

export default function TestCasesPage() {
  return (
    <AppShell
      title="Test Cases"
      subtitle="Generate, review, and approve QA test cases"
    >
      <Suspense fallback={<LoadingState message="Loading test cases…" />}>
        <TestCaseDashboard />
      </Suspense>
    </AppShell>
  );
}
