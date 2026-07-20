"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/ui.store";

const navItems: {
  href: string;
  label: string;
  disabled?: boolean;
}[] = [
  { href: ROUTES.DASHBOARD, label: "Dashboard" },
  { href: ROUTES.STORIES, label: "Stories" },
  { href: ROUTES.PROJECTS, label: "Projects" },
  { href: ROUTES.SPRINTS, label: "Sprints" },
  { href: ROUTES.TEST_CASES, label: "Test Cases" },
  { href: ROUTES.AUTOMATION, label: "Automation" },
  { href: ROUTES.SETTINGS, label: "Integrations" },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-1 flex-col gap-1 p-3">
      {navItems.map((item) => {
        const active = pathname.startsWith(item.href);
        if (item.disabled) {
          return (
            <span
              key={item.href}
              className="rounded-md px-3 py-2 text-sm text-muted/60"
              title="Coming in a later milestone"
            >
              {item.label}
            </span>
          );
        }
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent/10 text-accent"
                : "text-foreground hover:bg-surface-muted"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-56 shrink-0 border-r border-border bg-surface md:flex md:flex-col">
        <div className="border-b border-border px-4 py-5">
          <Link href={ROUTES.DASHBOARD} className="block">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              {APP_NAME}
            </p>
            <p className="mt-1 text-sm text-muted">Quality workspace</p>
          </Link>
        </div>
        <NavLinks />
      </aside>

      {/* Mobile drawer */}
      {sidebarOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative flex h-full w-64 flex-col border-r border-border bg-surface shadow-lg">
            <div className="flex items-center justify-between border-b border-border px-4 py-4">
              <Link
                href={ROUTES.DASHBOARD}
                onClick={() => setSidebarOpen(false)}
                className="block"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
                  {APP_NAME}
                </p>
              </Link>
              <button
                type="button"
                className="rounded px-2 py-1 text-sm text-muted hover:bg-surface-muted"
                onClick={() => setSidebarOpen(false)}
              >
                Close
              </button>
            </div>
            <NavLinks onNavigate={() => setSidebarOpen(false)} />
          </aside>
        </div>
      ) : null}
    </>
  );
}
