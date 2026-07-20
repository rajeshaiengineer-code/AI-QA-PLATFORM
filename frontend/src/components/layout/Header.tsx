"use client";

import Link from "next/link";

import { APP_NAME, ROUTES } from "@/lib/constants";
import { useUIStore } from "@/store/ui.store";

export function Header({
  title,
  subtitle = "Manage requirements that drive test generation",
}: {
  title: string;
  subtitle?: string;
}) {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/95 backdrop-blur">
      <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-md border border-border px-2 py-1 text-sm text-foreground md:hidden"
            aria-label="Open navigation"
            onClick={toggleSidebar}
          >
            Menu
          </button>
          <div className="md:hidden">
            <Link
              href={ROUTES.STORIES}
              className="text-sm font-semibold text-accent"
            >
              {APP_NAME}
            </Link>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground md:text-xl">
              {title}
            </h1>
            <p className="text-xs text-muted md:text-sm">{subtitle}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
