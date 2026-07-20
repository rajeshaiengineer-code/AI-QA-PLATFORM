import type { Metadata } from "next";
import { Suspense } from "react";

import { AutomationDashboard } from "@/components/automation/AutomationDashboard";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/ui/Feedback";

export const metadata: Metadata = {
  title: "Automation",
};

export default function AutomationPage() {
  return (
    <AppShell
      title="Automation"
      subtitle="BDD, Playwright artifacts, stub runs, and failure follow-up"
    >
      <Suspense fallback={<LoadingState message="Loading automation…" />}>
        <AutomationDashboard />
      </Suspense>
    </AppShell>
  );
}
