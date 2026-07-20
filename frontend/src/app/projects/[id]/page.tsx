import { AppShell } from "@/components/layout/AppShell";
import { ProjectDetail } from "@/components/projects/ProjectDetail";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <AppShell
      title="Project dashboard"
      subtitle="Story and sprint overview for this project"
    >
      <ProjectDetail projectId={id} />
    </AppShell>
  );
}
