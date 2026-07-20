import type { Metadata } from "next";

import { JiraConnectPanel } from "@/components/integrations/JiraConnectPanel";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "Integrations",
};

export default function IntegrationsPage() {
  return (
    <AppShell
      title="Integrations"
      subtitle="Connect external tools such as Jira Cloud"
    >
      <div className="mx-auto max-w-3xl space-y-6">
        <JiraConnectPanel />
      </div>
    </AppShell>
  );
}
