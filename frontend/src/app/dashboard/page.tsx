import { AppShell } from "@/components/layout/AppShell";
import { ReportingDashboard } from "@/components/dashboard/ReportingDashboard";

export default function DashboardPage() {
  return (
    <AppShell
      title="Dashboard"
      subtitle="Org and project quality metrics"
    >
      <ReportingDashboard />
    </AppShell>
  );
}
