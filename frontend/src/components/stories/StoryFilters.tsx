"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Select } from "@/components/ui/Select";
import { SearchBar } from "@/components/ui/SearchBar";
import { Button } from "@/components/ui/Button";
import { useStoryStore } from "@/store/story.store";
import {
  PRIORITY_OPTIONS,
  STORY_STATUS_OPTIONS,
  STORY_TYPE_OPTIONS,
} from "@/types/story";

export function StoryFilters() {
  const searchParams = useSearchParams();
  const { filters, setFilters, resetFilters } = useStoryStore();
  const [searchDraft, setSearchDraft] = useState(filters.search);

  useEffect(() => {
    const projectFromUrl = searchParams.get("project_id")?.trim();
    if (projectFromUrl && projectFromUrl !== filters.project_id) {
      setFilters({ project_id: projectFromUrl, page: 1 });
    }
  }, [searchParams, filters.project_id, setFilters]);

  useEffect(() => {
    setSearchDraft(filters.search);
  }, [filters.search]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (searchDraft !== filters.search) {
        setFilters({ search: searchDraft });
      }
    }, 300);
    return () => window.clearTimeout(handle);
  }, [searchDraft, filters.search, setFilters]);

  const hasActiveFilters = useMemo(
    () =>
      Boolean(
        filters.search ||
          filters.status ||
          filters.story_type ||
          filters.priority ||
          filters.project_id ||
          filters.sprint_id
      ),
    [filters]
  );

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface p-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SearchBar
          value={searchDraft}
          onChange={setSearchDraft}
          placeholder="Search by title or story key..."
          className="md:col-span-2 xl:col-span-2"
        />
        <Select
          label="Status"
          placeholder="All statuses"
          options={STORY_STATUS_OPTIONS}
          value={filters.status}
          onChange={(e) =>
            setFilters({ status: e.target.value as typeof filters.status })
          }
        />
        <Select
          label="Type"
          placeholder="All types"
          options={STORY_TYPE_OPTIONS}
          value={filters.story_type}
          onChange={(e) =>
            setFilters({
              story_type: e.target.value as typeof filters.story_type,
            })
          }
        />
        <Select
          label="Priority"
          placeholder="All priorities"
          options={PRIORITY_OPTIONS}
          value={filters.priority}
          onChange={(e) =>
            setFilters({ priority: e.target.value as typeof filters.priority })
          }
        />
        <label className="flex w-full flex-col gap-1.5 text-sm">
          <span className="font-medium text-foreground">Project ID</span>
          <input
            value={filters.project_id}
            onChange={(e) => setFilters({ project_id: e.target.value.trim() })}
            placeholder="Filter by project UUID"
            className="h-10 rounded-md border border-border bg-surface px-3 text-sm"
          />
        </label>
        <label className="flex w-full flex-col gap-1.5 text-sm">
          <span className="font-medium text-foreground">Sprint ID</span>
          <input
            value={filters.sprint_id}
            onChange={(e) => setFilters({ sprint_id: e.target.value.trim() })}
            placeholder="Filter by sprint UUID"
            className="h-10 rounded-md border border-border bg-surface px-3 text-sm"
          />
        </label>
      </div>
      {hasActiveFilters ? (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            Clear filters
          </Button>
        </div>
      ) : null}
    </div>
  );
}
