import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/ui/Feedback";

export default function StoriesLoading() {
  return (
    <AppShell title="Story Management">
      <LoadingState message="Loading story workspace…" />
    </AppShell>
  );
}
