import { AppShell } from "@/components/layout/AppShell";
import { ProjectDashboard } from "@/components/projects/ProjectDashboard";

export default function ProjectsPage() {
  return (
    <AppShell
      title="Projects"
      subtitle="Organize QA work by product and application"
    >
      <ProjectDashboard />
    </AppShell>
  );
}
