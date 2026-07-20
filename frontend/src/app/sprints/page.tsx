import { Suspense } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { SprintDashboard } from "@/components/sprints/SprintDashboard";
import { LoadingState } from "@/components/ui/Feedback";

export default function SprintsPage() {
  return (
    <AppShell
      title="Sprints"
      subtitle="Plan iterations and relate stories to delivery windows"
    >
      <Suspense fallback={<LoadingState message="Loading sprints…" />}>
        <SprintDashboard />
      </Suspense>
    </AppShell>
  );
}
