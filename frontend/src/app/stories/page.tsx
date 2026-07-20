import type { Metadata } from "next";
import { Suspense } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { StoryDashboard } from "@/components/stories/StoryDashboard";
import { LoadingState } from "@/components/ui/Feedback";

export const metadata: Metadata = {
  title: "Stories",
};

export default function StoriesPage() {
  return (
    <AppShell title="Story Management">
      <Suspense fallback={<LoadingState message="Loading stories…" />}>
        <StoryDashboard />
      </Suspense>
    </AppShell>
  );
}
