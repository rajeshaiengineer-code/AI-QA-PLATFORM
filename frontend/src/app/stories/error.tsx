"use client";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/Feedback";

export default function StoriesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <AppShell title="Story Management">
      <ErrorState
        title="Story page failed to load"
        message={error.message || "An unexpected error occurred."}
        onRetry={reset}
      />
      <div className="mt-4 flex justify-center">
        <Button variant="secondary" onClick={reset}>
          Reload
        </Button>
      </div>
    </AppShell>
  );
}
